"""
Rotas de Auditoria — Genesys Cloud Platform Audit API
=====================================================

Endpoints expostos ao frontend:

  GET  /audits/services
      Descobre quais dados de auditoria existem na org (serviceName ->
      entityTypes -> actions), via GET {BASE_URL}/audits/query/servicemapping.
      Use isso para popular os selects do frontend dinamicamente.

  POST /audits/search
      Cria a consulta assíncrona (POST /audits/query), faz polling do
      status (GET /audits/query/{transactionId}) até "Succeeded" e
      devolve a primeira página de resultados junto com o cursor.

  GET  /audits/search/{transaction_id}/results
      Paginação via cursor (GET /audits/query/{tid}/results).

Permissão necessária na OAuth Client Credentials: audits > audit > view
(role com essa permissão atribuída à integração).
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth import get_token, h
from auth_local import get_current_user
from config import BASE_URL

router = APIRouter()

# A busca "Por pessoa" faz fan-out concorrente em vários serviços (até 3 em
# paralelo) + varredura de múltiplas páginas por serviço — sob carga, a
# Genesys devolve 429 com o tempo de espera sugerido. Retentamos automático
# em vez de propagar o erro pro usuário, já que é um limite transitório.
MAX_RETRIES = 5
DEFAULT_RETRY_SECONDS = 2.0


def _retry_after_seconds(resp: httpx.Response) -> float:
    """Extrai o tempo de espera sugerido pela Genesys num 429."""
    header = resp.headers.get("Retry-After")
    if header:
        try:
            return max(float(header), 0.5)
        except ValueError:
            pass
    # Formato observado no corpo: {"message": "... Retry the request in [3] seconds", ...}
    try:
        message = resp.json().get("message", "")
        match = re.search(r"\[(\d+(?:\.\d+)?)\]", message)
        if match:
            return max(float(match.group(1)), 0.5)
    except Exception:
        pass
    return DEFAULT_RETRY_SECONDS


async def genesys_request(
    method: str,
    path: str,
    *,
    json: Optional[dict] = None,
    params: Optional[dict] = None,
) -> Any:
    token = await get_token()
    headers = h(token)

    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(MAX_RETRIES + 1):
            resp = await client.request(
                method, f"{BASE_URL}{path}", json=json, params=params, headers=headers
            )
            if resp.status_code != 429 or attempt == MAX_RETRIES:
                break
            await asyncio.sleep(_retry_after_seconds(resp))

    if resp.status_code == 403:
        raise HTTPException(
            403,
            "Integração sem permissão 'audits:audit:view'. "
            "Adicione a permissão à role da OAuth Client Credentials.",
        )
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, f"Genesys API: {resp.text[:300]}")
    return resp.json() if resp.text else {}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class AuditFilter(BaseModel):
    property: str  # ex: "EntityType", "Action", "UserId", "EntityId"
    value: str


class AuditSearchRequest(BaseModel):
    interval_start: str = Field(..., description="ISO 8601, ex: 2026-07-01T00:00:00Z")
    interval_end: str = Field(..., description="ISO 8601, ex: 2026-07-11T23:59:59Z")
    service_name: str = Field(..., description="Ex: PeoplePermissions, ContactCenter")
    filters: list[AuditFilter] = Field(default_factory=list)
    page_size: int = Field(default=50, ge=1, le=500)
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class AuditDeepSearchRequest(AuditSearchRequest):
    match_value: str = Field(..., description="UUID a localizar dentro dos eventos (ex: id da pessoa)")
    max_pages: int = Field(default=10, ge=1, le=50)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _create_and_poll(payload: dict) -> tuple[str, str]:
    """Cria a consulta assíncrona e faz polling até Succeeded/Failed/Cancelled."""
    created = await genesys_request("POST", "/audits/query", json=payload)
    transaction_id = created.get("id")
    if not transaction_id:
        raise HTTPException(502, "Genesys não retornou o id da transação.")

    state = created.get("state", "Queued")
    for _ in range(15):
        if state == "Succeeded":
            break
        if state in ("Failed", "Cancelled"):
            raise HTTPException(502, f"Consulta de auditoria terminou como {state}.")
        await asyncio.sleep(2)
        status = await genesys_request("GET", f"/audits/query/{transaction_id}")
        state = status.get("state", state)
    return transaction_id, state


def _enrich_group_membership_direction(batch: list[dict]) -> None:
    """
    A Genesys nunca expõe se um propertyChange "group-membership" (serviço
    Groups) foi uma adição ou remoção: newValues sempre traz o(s) UUID(s) do(s)
    membro(s) afetado(s) e oldValues sempre vem vazio, nos dois casos —
    confirmado empiricamente (explorar_auditoria.py --amostra Groups, 30 dias,
    104/104 ocorrências). O único sinal de direção é o evento SYSTEM irmão
    "memberCount" (mesmo context.correlationId): a contagem sobe numa adição e
    desce numa remoção. Anotamos aqui o evento "group-membership" com essa
    direção inferida (campo `_groupMembershipDirection`, não existe na API da
    Genesys), sem alterar o resto do evento. Requer que os dois eventos caiam
    na mesma página/lote — acontecem em sequência (~1-2s), então normalmente
    caem juntos; se não caírem, o evento simplesmente fica sem a anotação.
    """
    delta_by_correlation: dict[str, int] = {}
    for e in batch:
        if e.get("serviceName") != "Groups":
            continue
        for pc in e.get("propertyChanges") or []:
            if pc.get("property") != "memberCount":
                continue
            cid = (e.get("context") or {}).get("correlationId")
            old_vals, new_vals = pc.get("oldValues") or [], pc.get("newValues") or []
            if not (cid and old_vals and new_vals):
                continue
            try:
                delta_by_correlation[cid] = int(new_vals[0]) - int(old_vals[0])
            except (TypeError, ValueError):
                continue

    if not delta_by_correlation:
        return
    for e in batch:
        if e.get("serviceName") != "Groups":
            continue
        for pc in e.get("propertyChanges") or []:
            if pc.get("property") != "group-membership":
                continue
            cid = (e.get("context") or {}).get("correlationId")
            delta = delta_by_correlation.get(cid)
            if delta:
                e["_groupMembershipDirection"] = "add" if delta > 0 else "remove"


async def _resolve_group_membership_directions(
    entities: list[dict], interval_start: str, interval_end: str
) -> None:
    """
    Fecha a lacuna que `_enrich_group_membership_direction` sozinha não
    resolve: a busca "por pessoa" (ações que ela fez) filtra o Genesys
    server-side por `UserId`, e esse filtro nativo EXCLUI o evento SYSTEM
    "memberCount" antes mesmo dele chegar aqui — confirmado empiricamente
    (memberCount não tem `user.id` preenchido, só `context.userid`, que o
    filtro UserId não usa). Sem o memberCount na resposta, não há nada pra
    `_enrich_group_membership_direction` correlacionar.

    Aqui, para cada grupo (`entity.id`) que tem um "group-membership" sem
    direção resolvida, fazemos uma consulta extra filtrada por
    EntityId+EntityType (que a Genesys aceita e que INCLUI eventos SYSTEM),
    buscamos só os memberCount daquele grupo no mesmo intervalo, e rodamos a
    correlação de novo. Os eventos memberCount buscados aqui são só um canal
    lateral — não entram na resposta final ao frontend.
    """
    _enrich_group_membership_direction(entities)
    pending: dict[str, str] = {}  # group_id -> entityType
    for e in entities:
        if e.get("serviceName") != "Groups" or "_groupMembershipDirection" in e:
            continue
        if not any(pc.get("property") == "group-membership" for pc in e.get("propertyChanges") or []):
            continue
        group_id = e.get("entity", {}).get("id")
        if group_id:
            pending[group_id] = e.get("entityType") or "DirectoryGroup"
    if not pending:
        return

    supplemental: list[dict] = []
    for group_id, entity_type in pending.items():
        try:
            transaction_id, state = await _create_and_poll({
                "interval": f"{interval_start}/{interval_end}",
                "serviceName": "Groups",
                "filters": [
                    {"property": "EntityId", "value": group_id},
                    {"property": "EntityType", "value": entity_type},
                ],
            })
            if state != "Succeeded":
                continue
            page = await genesys_request(
                "GET", f"/audits/query/{transaction_id}/results", params={"pageSize": 200}
            )
        except HTTPException:
            continue
        supplemental.extend(page.get("entities", []))

    if supplemental:
        _enrich_group_membership_direction(entities + supplemental)


def _event_matches(event: dict, match_value: str) -> bool:
    """
    Procura match_value (tipicamente um UUID de pessoa) em campos onde a
    Audit API o embute sem oferecer filtro nativo. Confirmado empiricamente
    (explorar_auditoria.py) que o formato varia por serviço:
      - PeoplePermissions/Role (MemberAdd/Remove): UUID em entity.name
        ("{userId}--{roleId}--{orgId}")
      - ContactCenter/Queue (MemberAdd/Remove/Update): UUID em
        propertyChanges[].property ("QueueMember/<queueId>:<userId>")
    Varremos os dois como superset seguro em vez de fixar o campo por serviço.
    """
    needle = match_value.lower()
    entity = event.get("entity") or {}
    haystacks = [str(entity.get("name") or ""), str(entity.get("id") or "")]
    for pc in event.get("propertyChanges") or []:
        haystacks.append(str(pc.get("property") or ""))
        haystacks.extend(str(v) for v in (pc.get("oldValues") or []))
        haystacks.extend(str(v) for v in (pc.get("newValues") or []))
    return any(needle in h.lower() for h in haystacks if h)


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------
@router.get("/services")
async def list_audit_services(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Mapa de serviços/entidades/ações disponíveis para auditoria na org.

    A API do Genesys devolve `serviceName` / `entityTypes` / `entityType`;
    normalizamos para `name` / `entities` para consumo direto no frontend.
    """
    raw = await genesys_request("GET", "/audits/query/servicemapping")
    raw_list = raw if isinstance(raw, list) else raw.get("entities", raw.get("services", []))

    services = [
        {
            "name": item.get("serviceName", item.get("name")),
            "entities": [
                {
                    "name": et.get("entityType", et.get("name")),
                    "actions": et.get("actions", []),
                }
                for et in item.get("entityTypes", item.get("entities", []))
            ],
        }
        for item in raw_list
    ]
    return {"services": services}


@router.post("/search")
async def search_audits(
    body: AuditSearchRequest, current_user: dict = Depends(get_current_user)
) -> dict:
    """Cria a consulta, aguarda concluir e retorna a primeira página."""
    payload: dict[str, Any] = {
        "interval": f"{body.interval_start}/{body.interval_end}",
        "serviceName": body.service_name,
        "sort": [{"name": "Timestamp", "sortOrder": body.sort_order}],
    }
    if body.filters:
        payload["filters"] = [f.model_dump() for f in body.filters]

    transaction_id, state = await _create_and_poll(payload)

    if state != "Succeeded":
        # Frontend pode continuar consultando /results depois
        return {"transactionId": transaction_id, "state": state, "entities": []}

    results = await genesys_request(
        "GET",
        f"/audits/query/{transaction_id}/results",
        params={"pageSize": body.page_size, "expand": "user"},
    )
    entities = results.get("entities", [])
    if body.service_name == "Groups":
        await _resolve_group_membership_directions(entities, body.interval_start, body.interval_end)
    else:
        _enrich_group_membership_direction(entities)
    return {
        "transactionId": transaction_id,
        "state": "Succeeded",
        "cursor": results.get("cursor"),
        "pageSize": results.get("pageSize"),
        "entities": entities,
    }


@router.post("/search/deep")
async def deep_search_audits(
    body: AuditDeepSearchRequest, current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Varre os eventos de uma consulta e devolve só os que contêm match_value
    (ver `_event_matches`). Necessário para achar "fulano foi adicionado à
    fila/role X" — a Audit API não tem filtro nativo para isso, pois o alvo
    do evento é a fila/role, não a pessoa.

    Custo: até max_pages * page_size eventos baixados e varridos no backend.
    """
    payload: dict[str, Any] = {
        "interval": f"{body.interval_start}/{body.interval_end}",
        "serviceName": body.service_name,
        "sort": [{"name": "Timestamp", "sortOrder": body.sort_order}],
    }
    if body.filters:
        payload["filters"] = [f.model_dump() for f in body.filters]

    transaction_id, state = await _create_and_poll(payload)
    if state != "Succeeded":
        return {
            "transactionId": transaction_id,
            "state": state,
            "entities": [],
            "scanned": 0,
            "truncated": False,
        }

    matched: list[dict] = []
    scanned = 0
    cursor: Optional[str] = None
    truncated = False
    for page_num in range(body.max_pages):
        params: dict[str, Any] = {"pageSize": body.page_size, "expand": "user"}
        if cursor:
            params["cursor"] = cursor
        page = await genesys_request(
            "GET", f"/audits/query/{transaction_id}/results", params=params
        )
        batch = page.get("entities", [])
        scanned += len(batch)
        _enrich_group_membership_direction(batch)
        matched.extend(e for e in batch if _event_matches(e, body.match_value))
        cursor = page.get("cursor")
        if not cursor or not batch:
            break
        if page_num == body.max_pages - 1:
            truncated = True

    return {
        "transactionId": transaction_id,
        "state": "Succeeded",
        "entities": matched,
        "scanned": scanned,
        "truncated": truncated,
    }


class UserChangesRequest(BaseModel):
    user: str = Field(..., min_length=1, description="E-mail ou UUID do usuário")
    interval_start: str = Field(..., description="ISO 8601, ex: 2026-07-01T00:00:00Z")
    interval_end: str = Field(..., description="ISO 8601, ex: 2026-08-03T23:59:59Z")
    deep_categories: list[str] = Field(
        default_factory=list,
        description=(
            'Categorias de busca profunda: "queue" | "role" | "group". '
            "Default [] = só Directory/User (divisão). "
            "Com categorias, roda deep só nelas (sem Directory)."
        ),
    )
    deep_search: bool = Field(
        False,
        description=(
            "Compat: se true e deep_categories vazio/ausente, equivale a "
            '["queue","role","group"] + Directory. Preferir deep_categories.'
        ),
    )


@router.post("/user-changes")
async def user_changes(
    body: UserChangesRequest, current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Consolida alterações relevantes de um usuário no intervalo (máx. 30 dias).

    Sem deep_categories: só Directory/User (divisão).
    Com deep_categories: deep só nas categorias pedidas.
    Compat deep_search=true: Directory + queue/role/group.
    """
    from services.user_audit import get_user_changes

    # Compat: deep_search=true sem categorias → None (resolve usa as 3 + Directory).
    # Lista explícita (mesmo com deep_search) tem precedência e não inclui Directory.
    categories_arg: Optional[list[str]]
    if body.deep_categories:
        categories_arg = body.deep_categories
    elif body.deep_search:
        categories_arg = None
    else:
        categories_arg = []

    return await get_user_changes(
        body.user,
        body.interval_start,
        body.interval_end,
        deep_search=body.deep_search,
        deep_categories=categories_arg,
    )


@router.get("/search/{transaction_id}/results")
async def get_audit_results(
    transaction_id: str,
    cursor: Optional[str] = Query(default=None),
    page_size: int = Query(default=50, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Próximas páginas via cursor."""
    params: dict[str, Any] = {"pageSize": page_size, "expand": "user"}
    if cursor:
        params["cursor"] = cursor
    results = await genesys_request(
        "GET", f"/audits/query/{transaction_id}/results", params=params
    )
    entities = results.get("entities", [])
    # Página de continuação não carrega o intervalo original da busca — deriva
    # um intervalo com folga a partir dos próprios eventDate da página (os
    # eventos memberCount/individuals/group-membership de uma mesma mudança
    # ficam a poucos segundos um do outro, então a folga é generosa de propósito).
    dates = sorted(e["eventDate"] for e in entities if e.get("eventDate"))
    if dates:
        start = (datetime.fromisoformat(dates[0].replace("Z", "+00:00")) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end = (datetime.fromisoformat(dates[-1].replace("Z", "+00:00")) + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        await _resolve_group_membership_directions(entities, start, end)
    return {
        "transactionId": transaction_id,
        "cursor": results.get("cursor"),
        "entities": entities,
    }
