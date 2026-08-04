"""
Auditoria focada por usuário — grupo, role, divisão e fila.

Orquestra resolução do usuário, 4 consultas paralelas à Platform Audit API
e normalização em ChangeCards estáveis para o frontend.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from fastapi import HTTPException

from auth import get_token, h
from config import BASE_URL, DOMAIN
from routes.audits import (
    _create_and_poll,
    _enrich_group_membership_direction,
    _event_matches,
    _resolve_group_membership_directions,
    genesys_request,
)

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
UUID_PART = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
QUEUE_MEMBER_RE = re.compile(
    rf"^QueueMember/({UUID_PART}):({UUID_PART})(?::(joined))?$", re.IGNORECASE
)
ROLE_KEY_RE = re.compile(
    rf"^({UUID_PART})--({UUID_PART})--({UUID_PART})$", re.IGNORECASE
)
GROUP_MEMBERSHIP_UUID_RE = re.compile(UUID_PART, re.IGNORECASE)

GROUP_ENTITY_TYPES = frozenset(
    {"DirectoryGroup", "SkillGroup", "Team", "SkillGroupDefinition"}
)

SENTINELS = {
    "<queue member added>": "Membro adicionado à fila",
    "<queue member deleted>": "Membro removido da fila",
}

MAX_INTERVAL_DAYS = 30
DEEP_PAGE_SIZE = 250
DEEP_MAX_PAGES = 10
# Deep searches (Groups/Role/Queue) baixam eventos da org inteira e filtram
# o UUID localmente. Partir o intervalo evita falso truncated por volume da org.
DEEP_CHUNK_DAYS = 1
# Se uma janela diária ainda truncar, bisecta até este piso (segundos).
DEEP_MIN_CHUNK_SECONDS = 3600
# Pausa entre janelas deep — ContactCenter pode bisectar e gerar muitas queries.
DEEP_CHUNK_PAUSE_SECONDS = 0.4
MAP_PAGE_SIZE = 100
MAP_MAX_PAGES = 25
# Pool=1: deep + bisecção estoura 429 com concorrência entre serviços.
QUERY_POOL_SIZE = 1

NameMap = dict[str, str]


# ---------------------------------------------------------------------------
# Intervalo
# ---------------------------------------------------------------------------
def parse_iso(value: str) -> datetime:
    """Parse ISO-8601 (aceita Z ou offset)."""
    text = (value or "").strip()
    if not text:
        raise ValueError("data vazia")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def validate_interval(interval_start: str, interval_end: str) -> tuple[datetime, datetime]:
    """Valida intervalo: end > start e duração ≤ 30 dias."""
    try:
        start = parse_iso(interval_start)
        end = parse_iso(interval_end)
    except ValueError as exc:
        raise HTTPException(422, f"Data ISO inválida: {exc}") from exc
    if end <= start:
        raise HTTPException(422, "interval_end deve ser posterior a interval_start")
    if (end - start).total_seconds() > MAX_INTERVAL_DAYS * 86400:
        raise HTTPException(
            422,
            f"Intervalo máximo de {MAX_INTERVAL_DAYS} dias por consulta "
            "(limite da Platform Audit API).",
        )
    return start, end


def format_iso(dt: datetime) -> str:
    """UTC ISO-8601 com sufixo Z (formato aceito pela Platform Audit API)."""
    utc = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return utc.isoformat().replace("+00:00", "Z")


def iter_interval_chunks(
    start: datetime,
    end: datetime,
    *,
    chunk_days: int = DEEP_CHUNK_DAYS,
) -> list[tuple[str, str]]:
    """
    Parte [start, end) em janelas de até `chunk_days` dias.
    A última janela pode ser menor. Retorna pares (start_iso, end_iso).
    """
    if chunk_days < 1:
        raise ValueError("chunk_days deve ser >= 1")
    if end <= start:
        return []
    chunks: list[tuple[str, str]] = []
    cursor = start
    step = timedelta(days=chunk_days)
    while cursor < end:
        chunk_end = min(cursor + step, end)
        chunks.append((format_iso(cursor), format_iso(chunk_end)))
        cursor = chunk_end
    return chunks


# ---------------------------------------------------------------------------
# Resolução de usuário
# ---------------------------------------------------------------------------
async def resolve_user(user_ref: str) -> dict[str, Optional[str]]:
    """Resolve e-mail ou UUID para {id, name, email}."""
    q = (user_ref or "").strip().strip("{}")
    if not q:
        raise HTTPException(422, "Campo 'user' é obrigatório")

    token = await get_token()
    headers = h(token)

    async with httpx.AsyncClient(timeout=30) as client:
        if UUID_RE.match(q):
            resp = await client.get(f"{BASE_URL}/users/{q}", headers=headers)
            if resp.status_code == 404:
                raise HTTPException(404, "Usuário não encontrado")
            if resp.status_code >= 400:
                raise HTTPException(resp.status_code, f"Genesys API: {resp.text[:300]}")
            data = resp.json()
            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "email": data.get("email"),
            }

        email = q if "@" in q else f"{q}{DOMAIN}"
        payload = {
            "query": [
                {"fields": ["email"], "value": email, "type": "EXACT"},
                {
                    "fields": ["state"],
                    "values": ["active", "inactive"],
                    "type": "EXACT",
                    "operator": "OR",
                },
            ],
            "pageSize": 1,
        }
        resp = await client.post(
            f"{BASE_URL}/users/search", json=payload, headers=headers
        )
        if resp.status_code >= 400:
            raise HTTPException(resp.status_code, f"Genesys API: {resp.text[:300]}")
        results = resp.json().get("results") or []
        if not results:
            raise HTTPException(404, f"Usuário não encontrado: {email}")
        data = results[0]
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "email": data.get("email"),
        }


# ---------------------------------------------------------------------------
# Mapas de nomes (roles / groups / queues / divisions)
# ---------------------------------------------------------------------------
async def _fetch_id_name_map(path: str) -> NameMap:
    """Pagina GET path e devolve {id: name}."""
    token = await get_token()
    headers = h(token)
    out: NameMap = {}
    async with httpx.AsyncClient(timeout=30) as client:
        for page_number in range(1, MAP_MAX_PAGES + 1):
            url = f"{BASE_URL}{path}?pageSize={MAP_PAGE_SIZE}&pageNumber={page_number}"
            try:
                resp = await client.get(url, headers=headers)
            except httpx.HTTPError:
                break
            if resp.status_code >= 400:
                break
            data = resp.json()
            entities = data.get("entities") or []
            for e in entities:
                eid = e.get("id")
                if eid:
                    out[eid] = e.get("name") or eid
            page_count = data.get("pageCount", 1)
            if not entities or page_number >= page_count:
                break
    return out


async def fetch_name_maps() -> dict[str, NameMap]:
    """Carrega mapas id→nome em paralelo (falhas degradam para mapa vazio)."""
    roles, groups, queues, divisions = await asyncio.gather(
        _fetch_id_name_map("/authorization/roles"),
        _fetch_id_name_map("/groups"),
        _fetch_id_name_map("/routing/queues"),
        _fetch_id_name_map("/authorization/divisions"),
        return_exceptions=True,
    )
    empty: NameMap = {}
    return {
        "roles": roles if isinstance(roles, dict) else empty,
        "groups": groups if isinstance(groups, dict) else empty,
        "queues": queues if isinstance(queues, dict) else empty,
        "divisions": divisions if isinstance(divisions, dict) else empty,
    }


# ---------------------------------------------------------------------------
# Consultas de auditoria
# ---------------------------------------------------------------------------
async def _paginated_audit(
    *,
    service_name: str,
    filters: list[dict[str, str]],
    interval_start: str,
    interval_end: str,
    match_value: Optional[str] = None,
    page_size: int = DEEP_PAGE_SIZE,
    max_pages: int = DEEP_MAX_PAGES,
) -> tuple[list[dict], bool, int]:
    """
    Cria consulta, pagina results e opcionalmente filtra por match_value
    (busca profunda). Retorna (entities, truncated, scanned).
    """
    payload: dict[str, Any] = {
        "interval": f"{interval_start}/{interval_end}",
        "serviceName": service_name,
        "sort": [{"name": "Timestamp", "sortOrder": "desc"}],
    }
    if filters:
        payload["filters"] = filters

    transaction_id, state = await _create_and_poll(payload)
    if state != "Succeeded":
        return [], False, 0

    matched: list[dict] = []
    scanned = 0
    cursor: Optional[str] = None
    truncated = False

    for page_num in range(max_pages):
        params: dict[str, Any] = {"pageSize": page_size, "expand": "user"}
        if cursor:
            params["cursor"] = cursor
        page = await genesys_request(
            "GET", f"/audits/query/{transaction_id}/results", params=params
        )
        batch = page.get("entities") or []
        scanned += len(batch)
        _enrich_group_membership_direction(batch)
        if match_value:
            matched.extend(e for e in batch if _event_matches(e, match_value))
        else:
            matched.extend(batch)
        cursor = page.get("cursor")
        if not cursor or not batch:
            break
        if page_num == max_pages - 1:
            truncated = True

    return matched, truncated, scanned


async def _deep_audit_window(
    *,
    service_name: str,
    filters: list[dict[str, str]],
    interval_start: str,
    interval_end: str,
    match_value: str,
) -> tuple[list[dict], bool, int]:
    """
    Consulta uma janela; se truncar, bisecta e reconsulta as metades
    (descarta o resultado parcial da janela truncada). truncated só
    permanece true se a janela já estiver no piso DEEP_MIN_CHUNK_SECONDS.
    """
    matched, truncated, scanned = await _paginated_audit(
        service_name=service_name,
        filters=filters,
        interval_start=interval_start,
        interval_end=interval_end,
        match_value=match_value,
    )
    if not truncated:
        return matched, False, scanned

    start = parse_iso(interval_start)
    end = parse_iso(interval_end)
    if (end - start).total_seconds() <= DEEP_MIN_CHUNK_SECONDS:
        return matched, True, scanned

    mid = start + (end - start) / 2
    left_m, left_t, left_s = await _deep_audit_window(
        service_name=service_name,
        filters=filters,
        interval_start=format_iso(start),
        interval_end=format_iso(mid),
        match_value=match_value,
    )
    if DEEP_CHUNK_PAUSE_SECONDS > 0:
        await asyncio.sleep(DEEP_CHUNK_PAUSE_SECONDS)
    right_m, right_t, right_s = await _deep_audit_window(
        service_name=service_name,
        filters=filters,
        interval_start=format_iso(mid),
        interval_end=format_iso(end),
        match_value=match_value,
    )
    # scanned das metades substitui o da janela truncada (reconsulta completa)
    return left_m + right_m, left_t or right_t, left_s + right_s


async def _deep_audit_chunked(
    *,
    service_name: str,
    filters: list[dict[str, str]],
    start: datetime,
    end: datetime,
    match_value: str,
) -> tuple[list[dict], bool, int]:
    """
    Busca profunda em janelas diárias (sequencial por serviço).

    `truncated` só fica true se alguma janela (após bisecção até 1h)
    ainda estourar DEEP_MAX_PAGES×DEEP_PAGE_SIZE — não pelo volume
    acumulado do intervalo inteiro.
    """
    all_matched: list[dict] = []
    total_scanned = 0
    any_window_truncated = False

    chunks = iter_interval_chunks(start, end)
    for i, (chunk_start, chunk_end) in enumerate(chunks):
        if i > 0 and DEEP_CHUNK_PAUSE_SECONDS > 0:
            await asyncio.sleep(DEEP_CHUNK_PAUSE_SECONDS)
        matched, truncated, scanned = await _deep_audit_window(
            service_name=service_name,
            filters=filters,
            interval_start=chunk_start,
            interval_end=chunk_end,
            match_value=match_value,
        )
        all_matched.extend(matched)
        total_scanned += scanned
        if truncated:
            any_window_truncated = True

    return all_matched, any_window_truncated, total_scanned


async def _run_pool(coros: list, concurrency: int = QUERY_POOL_SIZE) -> list:
    sem = asyncio.Semaphore(concurrency)

    async def _wrap(coro):
        async with sem:
            return await coro

    return list(await asyncio.gather(*(_wrap(c) for c in coros), return_exceptions=True))


# ---------------------------------------------------------------------------
# Normalização → ChangeCard
# ---------------------------------------------------------------------------
def _lookup(name_map: NameMap, entity_id: Optional[str], fallback: Optional[str] = None) -> str:
    if not entity_id:
        return fallback or "—"
    return name_map.get(entity_id) or fallback or entity_id


def _changed_by(event: dict) -> dict[str, Any]:
    if (event.get("level") or "").upper() == "SYSTEM":
        return {"id": None, "name": None, "kind": "SYSTEM"}
    user = event.get("user") or {}
    if user.get("id"):
        return {
            "id": user.get("id"),
            "name": user.get("name"),
            "kind": "USER",
        }
    return {"id": None, "name": None, "kind": "UNKNOWN"}


def _base_card(event: dict, *, category: str, action: str, resource: dict,
               before: Optional[str], after: Optional[str]) -> dict:
    return {
        "id": event.get("id"),
        "category": category,
        "action": action,
        "resource": resource,
        "before": before,
        "after": after,
        "changed_by": _changed_by(event),
        "event_date": event.get("eventDate"),
    }


def _parse_queue_member(property_name: str) -> Optional[dict]:
    m = QUEUE_MEMBER_RE.match(property_name or "")
    if not m:
        return None
    return {"queue_id": m.group(1), "user_id": m.group(2), "joined": bool(m.group(3))}


def _parse_role_key(name: str) -> Optional[dict]:
    m = ROLE_KEY_RE.match(name or "")
    if not m:
        return None
    return {"user_id": m.group(1), "role_id": m.group(2), "org_id": m.group(3)}


def _parse_group_membership_ids(value: str) -> list[str]:
    return GROUP_MEMBERSHIP_UUID_RE.findall(value or "")


def _humanize_queue_value(value: Optional[str], *, joined: bool) -> Optional[str]:
    if value is None or value == "":
        return None
    if value in SENTINELS:
        return SENTINELS[value]
    if joined:
        if value == "true":
            return "ativo na fila"
        if value == "false":
            return "inativo na fila"
    return value


def _card_queue(event: dict, maps: dict[str, NameMap]) -> Optional[dict]:
    action_raw = event.get("action") or ""
    member = None
    joined_change = None
    for pc in event.get("propertyChanges") or []:
        parsed = _parse_queue_member(pc.get("property") or "")
        if not parsed:
            continue
        if parsed["joined"] and joined_change is None:
            joined_change = {**parsed, "pc": pc}
        if member is None:
            member = {**parsed, "pc": pc}

    entity = event.get("entity") or {}
    queue_id = (joined_change or member or {}).get("queue_id") or entity.get("id")
    queue_name = _lookup(maps["queues"], queue_id, entity.get("name"))
    resource = {"id": queue_id, "name": queue_name, "type": "Queue"}

    if joined_change and action_raw == "MemberUpdate":
        pc = joined_change["pc"]
        old_v = (pc.get("oldValues") or [None])[0]
        new_v = (pc.get("newValues") or [None])[0]
        if new_v == "false":
            action = "deactivate"
        elif new_v == "true":
            action = "activate"
        else:
            action = "update"
        return _base_card(
            event,
            category="queue",
            action=action,
            resource=resource,
            before=_humanize_queue_value(old_v, joined=True),
            after=_humanize_queue_value(new_v, joined=True),
        )

    if not member:
        return None

    pc = member["pc"]
    old_v = (pc.get("oldValues") or [None])[0]
    new_v = (pc.get("newValues") or [None])[0]

    if action_raw == "MemberAdd":
        return _base_card(
            event,
            category="queue",
            action="add",
            resource=resource,
            before=None,
            after=_humanize_queue_value(new_v, joined=False) or "Membro adicionado à fila",
        )
    if action_raw == "MemberRemove":
        return _base_card(
            event,
            category="queue",
            action="remove",
            resource=resource,
            before=_humanize_queue_value(old_v, joined=False) or "Membro removido da fila",
            after=None,
        )
    return _base_card(
        event,
        category="queue",
        action="update",
        resource=resource,
        before=_humanize_queue_value(old_v, joined=False),
        after=_humanize_queue_value(new_v, joined=False),
    )


def _card_role(event: dict, maps: dict[str, NameMap]) -> Optional[dict]:
    action_raw = event.get("action") or ""
    entity = event.get("entity") or {}
    key = _parse_role_key(entity.get("name") or "")
    role_id = (key or {}).get("role_id") or entity.get("id")
    if not role_id:
        return None
    role_name = _lookup(maps["roles"], role_id)
    resource = {"id": role_id, "name": role_name, "type": "Role"}

    if action_raw == "MemberAdd":
        return _base_card(
            event,
            category="role",
            action="add",
            resource=resource,
            before=None,
            after=role_name,
        )
    if action_raw == "MemberRemove":
        return _base_card(
            event,
            category="role",
            action="remove",
            resource=resource,
            before=role_name,
            after=None,
        )
    # propertyChanges vem vazio em Role — outros actions não viram card de membership
    return None


def _card_group(event: dict, maps: dict[str, NameMap]) -> Optional[dict]:
    membership = next(
        (
            pc
            for pc in (event.get("propertyChanges") or [])
            if pc.get("property") == "group-membership"
        ),
        None,
    )
    if not membership:
        return None  # descarta individuals, memberCount, version, etc.

    entity = event.get("entity") or {}
    group_id = entity.get("id")
    group_name = _lookup(maps["groups"], group_id, entity.get("name"))
    resource = {
        "id": group_id,
        "name": group_name,
        "type": event.get("entityType") or "DirectoryGroup",
    }

    direction = event.get("_groupMembershipDirection")
    if direction == "add":
        return _base_card(
            event,
            category="group",
            action="add",
            resource=resource,
            before=None,
            after=group_name,
        )
    if direction == "remove":
        return _base_card(
            event,
            category="group",
            action="remove",
            resource=resource,
            before=group_name,
            after=None,
        )
    # Direção desconhecida — ainda devolvemos o card com ação neutra
    return _base_card(
        event,
        category="group",
        action="update",
        resource=resource,
        before=None,
        after=group_name,
    )


def _card_division(event: dict, maps: dict[str, NameMap]) -> Optional[dict]:
    division_pc = next(
        (
            pc
            for pc in (event.get("propertyChanges") or [])
            if pc.get("property") == "divisionId"
        ),
        None,
    )
    if not division_pc:
        return None  # descarta version, addresses, etc.

    old_id = (division_pc.get("oldValues") or [None])[0]
    new_id = (division_pc.get("newValues") or [None])[0]
    if not old_id and not new_id:
        return None

    resource_id = new_id or old_id
    resource = {
        "id": resource_id,
        "name": _lookup(maps["divisions"], resource_id),
        "type": "Division",
    }
    return _base_card(
        event,
        category="division",
        action="update",
        resource=resource,
        before=_lookup(maps["divisions"], old_id) if old_id else None,
        after=_lookup(maps["divisions"], new_id) if new_id else None,
    )


def to_change_card(
    event: dict, maps: Optional[dict[str, NameMap]] = None
) -> Optional[dict]:
    """
    Normaliza um evento bruto da Audit API em ChangeCard, ou None se for ruído
    (individuals, version, Directory sem divisionId, etc.).
    """
    maps = maps or {"roles": {}, "groups": {}, "queues": {}, "divisions": {}}
    service = event.get("serviceName")
    entity_type = event.get("entityType")

    if service == "ContactCenter" and entity_type == "Queue":
        return _card_queue(event, maps)
    if service == "PeoplePermissions" and entity_type == "Role":
        return _card_role(event, maps)
    if service == "Groups" and entity_type in GROUP_ENTITY_TYPES:
        return _card_group(event, maps)
    if service == "Directory" and entity_type == "User":
        return _card_division(event, maps)
    return None


# Categorias de deep search aceitas pela API (fila / role / grupo).
DEEP_CATEGORY_QUEUE = "queue"
DEEP_CATEGORY_ROLE = "role"
DEEP_CATEGORY_GROUP = "group"
ALL_DEEP_CATEGORIES = (
    DEEP_CATEGORY_QUEUE,
    DEEP_CATEGORY_ROLE,
    DEEP_CATEGORY_GROUP,
)
def resolve_deep_categories(
    deep_categories: Optional[list[str]] = None,
    *,
    deep_search: bool = False,
) -> list[str]:
    """
    Normaliza categorias deep pedidas.

    Compat: deep_search=True sem deep_categories → as 3 categorias.
    deep_categories explícito tem precedência sobre o boolean.
    """
    if deep_categories is not None:
        seen: list[str] = []
        invalid: list[str] = []
        for raw in deep_categories:
            cat = (raw or "").strip().lower()
            if not cat:
                continue
            if cat not in ALL_DEEP_CATEGORIES:
                invalid.append(raw)
                continue
            if cat not in seen:
                seen.append(cat)
        if invalid:
            raise HTTPException(
                422,
                f"deep_categories inválidas: {invalid}. "
                f"Use: {list(ALL_DEEP_CATEGORIES)}",
            )
        return seen
    if deep_search:
        return list(ALL_DEEP_CATEGORIES)
    return []


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------
async def get_user_changes(
    user_ref: str,
    interval_start: str,
    interval_end: str,
    *,
    deep_search: bool = False,
    deep_categories: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Resolve o usuário e devolve ChangeCards.

    Sem deep_categories (e deep_search=False): só Directory/User (divisão).
    Com deep_categories: deep apenas nas categorias pedidas (sem Directory).
    Compat deep_search=True: Directory + as 3 categorias deep.
    """
    start, end = validate_interval(interval_start, interval_end)
    categories = resolve_deep_categories(deep_categories, deep_search=deep_search)
    # Compat: deep_search=True sem lista explícita ainda inclui Directory.
    include_directory = not categories or (
        deep_search and deep_categories is None
    )

    user, maps = await asyncio.gather(
        resolve_user(user_ref),
        fetch_name_maps(),
    )
    user_id = user["id"]
    if not user_id:
        raise HTTPException(502, "Usuário resolvido sem id")

    queries: list[Any] = []
    service_keys: list[str] = []

    if include_directory:
        # Divisão: filtro nativo EntityId + EntityType=User (intervalo inteiro)
        queries.append(
            _paginated_audit(
                service_name="Directory",
                filters=[
                    {"property": "EntityId", "value": user_id},
                    {"property": "EntityType", "value": "User"},
                ],
                interval_start=interval_start,
                interval_end=interval_end,
                match_value=None,
            )
        )
        service_keys.append("Directory")

    # Grupo / role / fila: deep search em janelas diárias (filtro local por UUID)
    if DEEP_CATEGORY_GROUP in categories:
        queries.append(
            _deep_audit_chunked(
                service_name="Groups",
                filters=[{"property": "EntityType", "value": "DirectoryGroup"}],
                start=start,
                end=end,
                match_value=user_id,
            )
        )
        service_keys.append("Groups")
    if DEEP_CATEGORY_ROLE in categories:
        queries.append(
            _deep_audit_chunked(
                service_name="PeoplePermissions",
                filters=[{"property": "EntityType", "value": "Role"}],
                start=start,
                end=end,
                match_value=user_id,
            )
        )
        service_keys.append("PeoplePermissions")
    if DEEP_CATEGORY_QUEUE in categories:
        queries.append(
            _deep_audit_chunked(
                service_name="ContactCenter",
                filters=[{"property": "EntityType", "value": "Queue"}],
                start=start,
                end=end,
                match_value=user_id,
            )
        )
        service_keys.append("ContactCenter")

    results = await _run_pool(queries, QUERY_POOL_SIZE)

    scanned_by_service: dict[str, Any] = {}
    truncated_by_service: dict[str, bool] = {}
    all_events: list[dict] = []
    any_truncated = False
    errors: list[str] = []

    for key, result in zip(service_keys, results):
        if isinstance(result, Exception):
            scanned_by_service[key] = {"error": str(result), "scanned": 0, "matched": 0}
            truncated_by_service[key] = False
            errors.append(f"{key}: {result}")
            continue
        entities, truncated, scanned = result
        if key == "Groups" and entities:
            await _resolve_group_membership_directions(
                entities, interval_start, interval_end
            )
        all_events.extend(entities)
        scanned_by_service[key] = {
            "scanned": scanned,
            "matched": len(entities),
            "truncated": truncated,
        }
        truncated_by_service[key] = truncated
        if truncated:
            any_truncated = True

    # Serviços não pedidos: marcar omitted (motivo distinto por caso)
    all_services = ("Directory", "Groups", "PeoplePermissions", "ContactCenter")
    for svc in all_services:
        if svc in scanned_by_service:
            continue
        if svc == "Directory":
            reason = "not_in_request"
        elif not categories:
            reason = "deep_search_off"
        else:
            reason = "not_requested"
        scanned_by_service[svc] = {"omitted": True, "reason": reason}
        truncated_by_service[svc] = False

    # Dedupe por id do evento (fan-out pode sobrepor em edge cases)
    seen: set[str] = set()
    changes: list[dict] = []
    for ev in all_events:
        eid = ev.get("id")
        if eid and eid in seen:
            continue
        card = to_change_card(ev, maps)
        if card is None:
            continue
        if eid:
            seen.add(eid)
        changes.append(card)

    changes.sort(key=lambda c: c.get("event_date") or "", reverse=True)

    meta: dict[str, Any] = {
        "deep_categories": categories,
        # Compat: true se alguma categoria deep rodou
        "deep_search": bool(categories),
        "include_directory": include_directory,
        "truncated": any_truncated,
        "truncated_by_service": truncated_by_service,
        "scanned_by_service": scanned_by_service,
    }
    if errors:
        meta["errors"] = errors

    return {
        "user": user,
        "interval": {"start": interval_start, "end": interval_end},
        "changes": changes,
        "meta": meta,
    }
