"""Testes unitários do normalizador de ChangeCards (auditoria por usuário)."""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from services.user_audit import (
    MAX_INTERVAL_DAYS,
    _deep_audit_chunked,
    _deep_audit_window,
    get_user_changes,
    iter_interval_chunks,
    parse_iso,
    to_change_card,
    validate_interval,
)

USER_ID = "11111111-1111-1111-1111-111111111111"
ACTOR_ID = "22222222-2222-2222-2222-222222222222"
QUEUE_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
ROLE_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
ORG_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
GROUP_ID = "dddddddd-dddd-dddd-dddd-dddddddddddd"
DIV_OLD = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
DIV_NEW = "ffffffff-ffff-ffff-ffff-ffffffffffff"

MAPS = {
    "roles": {ROLE_ID: "Agent"},
    "groups": {GROUP_ID: "G_AZ_TEAM"},
    "queues": {QUEUE_ID: "Fila Vendas"},
    "divisions": {DIV_OLD: "Home", DIV_NEW: "Contact Center"},
}


def _event(**overrides):
    base = {
        "id": "evt-1",
        "eventDate": "2026-07-15T12:00:00.000Z",
        "level": "USER",
        "user": {"id": ACTOR_ID, "name": "Admin Ops"},
        "propertyChanges": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Intervalo
# ---------------------------------------------------------------------------
def test_validate_interval_ok():
    start, end = validate_interval(
        "2026-07-01T00:00:00Z", "2026-07-31T00:00:00Z"
    )
    assert (end - start).days == 30


def test_validate_interval_rejects_inverted():
    with pytest.raises(HTTPException) as exc:
        validate_interval("2026-08-01T00:00:00Z", "2026-07-01T00:00:00Z")
    assert exc.value.status_code == 422


def test_validate_interval_rejects_over_30_days():
    with pytest.raises(HTTPException) as exc:
        validate_interval("2026-07-01T00:00:00Z", "2026-08-01T00:01:01Z")
    assert exc.value.status_code == 422
    assert str(MAX_INTERVAL_DAYS) in exc.value.detail


def test_validate_interval_deep_rejects_over_48_hours():
    with pytest.raises(HTTPException) as exc:
        validate_interval(
            "2026-07-01T00:00:00Z", "2026-07-03T00:05:00Z", max_hours=48
        )
    assert exc.value.status_code == 422
    assert "48" in exc.value.detail


# ---------------------------------------------------------------------------
# Chunking (deep search)
# ---------------------------------------------------------------------------
def test_iter_interval_chunks_seven_days():
    start = parse_iso("2026-07-27T00:00:00Z")
    end = parse_iso("2026-08-03T00:00:00Z")
    chunks = iter_interval_chunks(start, end)
    assert len(chunks) == 7
    assert chunks[0] == ("2026-07-27T00:00:00Z", "2026-07-28T00:00:00Z")
    assert chunks[-1] == ("2026-08-02T00:00:00Z", "2026-08-03T00:00:00Z")
    # Janelas contíguas sem buraco
    for i in range(len(chunks) - 1):
        assert chunks[i][1] == chunks[i + 1][0]


def test_iter_interval_chunks_partial_last_window():
    start = parse_iso("2026-08-01T12:00:00Z")
    end = parse_iso("2026-08-02T18:00:00Z")
    chunks = iter_interval_chunks(start, end)
    assert len(chunks) == 2
    assert chunks[0] == ("2026-08-01T12:00:00Z", "2026-08-02T12:00:00Z")
    assert chunks[1] == ("2026-08-02T12:00:00Z", "2026-08-02T18:00:00Z")


@pytest.mark.asyncio
async def test_deep_audit_chunked_no_false_truncated(monkeypatch):
    """Volume alto no intervalo inteiro não marca truncated se cada janela cabe."""
    calls: list[tuple[str, str]] = []

    async def fake_paginated(**kwargs):
        calls.append((kwargs["interval_start"], kwargs["interval_end"]))
        # Cada janela escaneia o teto mas esgota o cursor (truncated=False)
        return [{"id": f"evt-{len(calls)}"}], False, 2500

    monkeypatch.setattr(
        "services.user_audit._paginated_audit", AsyncMock(side_effect=fake_paginated)
    )
    start = parse_iso("2026-07-27T00:00:00Z")
    end = parse_iso("2026-08-03T00:00:00Z")
    entities, truncated, scanned = await _deep_audit_chunked(
        service_name="Groups",
        filters=[{"property": "EntityType", "value": "DirectoryGroup"}],
        start=start,
        end=end,
        match_value=USER_ID,
    )
    assert len(calls) == 7
    assert truncated is False
    assert scanned == 2500 * 7
    assert len(entities) == 7


@pytest.mark.asyncio
async def test_deep_audit_window_bisects_when_truncated(monkeypatch):
    """Janela truncada é bipartida; truncated some se as metades cabem."""
    calls: list[tuple[str, str]] = []

    async def fake_paginated(**kwargs):
        s, e = kwargs["interval_start"], kwargs["interval_end"]
        calls.append((s, e))
        start = parse_iso(s)
        end = parse_iso(e)
        # Truncado só no dia cheio; metades (≤12h) completam
        if (end - start).total_seconds() > 12 * 3600:
            return [{"id": "partial"}], True, 2500
        return [{"id": f"ok-{len(calls)}"}], False, 800

    monkeypatch.setattr(
        "services.user_audit._paginated_audit", AsyncMock(side_effect=fake_paginated)
    )
    entities, truncated, scanned = await _deep_audit_window(
        service_name="ContactCenter",
        filters=[{"property": "EntityType", "value": "Queue"}],
        interval_start="2026-07-28T00:00:00Z",
        interval_end="2026-07-29T00:00:00Z",
        match_value=USER_ID,
    )
    assert truncated is False
    assert len(calls) == 3  # dia + 2 metades
    assert all(e["id"].startswith("ok-") for e in entities)
    assert scanned == 1600  # só as metades contam


@pytest.mark.asyncio
async def test_deep_audit_chunked_truncated_at_min_floor(monkeypatch):
    """truncated=true só se janela no piso (1h) ainda tiver cursor restante."""

    async def fake_paginated(**kwargs):
        return [{"id": "hot"}], True, 2500

    monkeypatch.setattr(
        "services.user_audit._paginated_audit", AsyncMock(side_effect=fake_paginated)
    )
    # Intervalo já no piso → não bisecta
    start = parse_iso("2026-07-28T12:00:00Z")
    end = start + timedelta(hours=1)
    entities, truncated, scanned = await _deep_audit_chunked(
        service_name="ContactCenter",
        filters=[{"property": "EntityType", "value": "Queue"}],
        start=start,
        end=end,
        match_value=USER_ID,
    )
    assert truncated is True
    assert any(e["id"] == "hot" for e in entities)
    assert scanned == 2500


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------
def test_normalize_queue_member_add():
    ev = _event(
        id="q-add",
        serviceName="ContactCenter",
        entityType="Queue",
        action="MemberAdd",
        entity={"id": QUEUE_ID, "name": "Fila Vendas"},
        propertyChanges=[
            {
                "property": f"QueueMember/{QUEUE_ID}:{USER_ID}",
                "oldValues": [],
                "newValues": ["<queue member added>"],
            }
        ],
    )
    card = to_change_card(ev, MAPS)
    assert card is not None
    assert card["category"] == "queue"
    assert card["action"] == "add"
    assert card["resource"] == {
        "id": QUEUE_ID,
        "name": "Fila Vendas",
        "type": "Queue",
    }
    assert card["before"] is None
    assert card["after"] == "Membro adicionado à fila"
    assert card["changed_by"]["kind"] == "USER"
    assert card["changed_by"]["name"] == "Admin Ops"
    assert card["event_date"] == "2026-07-15T12:00:00.000Z"


def test_normalize_queue_member_remove():
    ev = _event(
        id="q-rm",
        serviceName="ContactCenter",
        entityType="Queue",
        action="MemberRemove",
        entity={"id": QUEUE_ID, "name": "Fila Vendas"},
        propertyChanges=[
            {
                "property": f"QueueMember/{QUEUE_ID}:{USER_ID}",
                "oldValues": ["<queue member deleted>"],
                "newValues": [],
            }
        ],
    )
    card = to_change_card(ev, MAPS)
    assert card["action"] == "remove"
    assert card["before"] == "Membro removido da fila"
    assert card["after"] is None


def test_normalize_queue_deactivate():
    ev = _event(
        id="q-off",
        serviceName="ContactCenter",
        entityType="Queue",
        action="MemberUpdate",
        entity={"id": QUEUE_ID, "name": "Fila Vendas"},
        propertyChanges=[
            {
                "property": f"QueueMember/{QUEUE_ID}:{USER_ID}:joined",
                "oldValues": ["true"],
                "newValues": ["false"],
            }
        ],
    )
    card = to_change_card(ev, MAPS)
    assert card["action"] == "deactivate"
    assert card["before"] == "ativo na fila"
    assert card["after"] == "inativo na fila"


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------
def test_normalize_role_member_add():
    ev = _event(
        id="r-add",
        serviceName="PeoplePermissions",
        entityType="Role",
        action="MemberAdd",
        entity={
            "id": ROLE_ID,
            "name": f"{USER_ID}--{ROLE_ID}--{ORG_ID}",
        },
        propertyChanges=[],  # Role: propertyChanges sempre vazio
    )
    card = to_change_card(ev, MAPS)
    assert card is not None
    assert card["category"] == "role"
    assert card["action"] == "add"
    assert card["resource"]["name"] == "Agent"
    assert card["resource"]["type"] == "Role"
    assert card["before"] is None
    assert card["after"] == "Agent"


def test_normalize_role_member_remove():
    ev = _event(
        id="r-rm",
        serviceName="PeoplePermissions",
        entityType="Role",
        action="MemberRemove",
        entity={
            "id": ROLE_ID,
            "name": f"{USER_ID}--{ROLE_ID}--{ORG_ID}",
        },
    )
    card = to_change_card(ev, MAPS)
    assert card["action"] == "remove"
    assert card["before"] == "Agent"
    assert card["after"] is None


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------
def test_normalize_group_add():
    ev = _event(
        id="g-add",
        serviceName="Groups",
        entityType="DirectoryGroup",
        action="Update",
        entity={"id": GROUP_ID, "name": ""},
        _groupMembershipDirection="add",
        propertyChanges=[
            {
                "property": "group-membership",
                "oldValues": [],
                "newValues": [f"[{USER_ID}]"],
            },
            {"property": "individuals", "oldValues": [], "newValues": []},
        ],
    )
    card = to_change_card(ev, MAPS)
    assert card is not None
    assert card["category"] == "group"
    assert card["action"] == "add"
    assert card["resource"]["name"] == "G_AZ_TEAM"
    assert card["before"] is None
    assert card["after"] == "G_AZ_TEAM"


def test_normalize_group_remove():
    ev = _event(
        id="g-rm",
        serviceName="Groups",
        entityType="DirectoryGroup",
        action="Update",
        entity={"id": GROUP_ID},
        _groupMembershipDirection="remove",
        propertyChanges=[
            {
                "property": "group-membership",
                "oldValues": [],
                "newValues": [f"[{USER_ID}]"],
            }
        ],
    )
    card = to_change_card(ev, MAPS)
    assert card["action"] == "remove"
    assert card["before"] == "G_AZ_TEAM"
    assert card["after"] is None


def test_normalize_group_discards_individuals_only():
    """Evento só com 'individuals' (ruído) não vira card."""
    ev = _event(
        id="g-noise",
        serviceName="Groups",
        entityType="DirectoryGroup",
        action="Update",
        entity={"id": GROUP_ID},
        propertyChanges=[
            {"property": "individuals", "oldValues": [], "newValues": []},
        ],
    )
    assert to_change_card(ev, MAPS) is None


# ---------------------------------------------------------------------------
# Division
# ---------------------------------------------------------------------------
def test_normalize_division_change():
    ev = _event(
        id="d-1",
        serviceName="Directory",
        entityType="User",
        action="Update",
        entity={"id": USER_ID, "name": ""},
        propertyChanges=[
            {"property": "version", "oldValues": ["10"], "newValues": ["11"]},
            {
                "property": "divisionId",
                "oldValues": [DIV_OLD],
                "newValues": [DIV_NEW],
            },
        ],
    )
    card = to_change_card(ev, MAPS)
    assert card is not None
    assert card["category"] == "division"
    assert card["action"] == "update"
    assert card["before"] == "Home"
    assert card["after"] == "Contact Center"
    assert card["resource"]["type"] == "Division"
    assert card["resource"]["name"] == "Contact Center"


def test_normalize_directory_without_division_is_noise():
    ev = _event(
        id="d-noise",
        serviceName="Directory",
        entityType="User",
        action="Update",
        entity={"id": USER_ID},
        propertyChanges=[
            {"property": "version", "oldValues": ["1"], "newValues": ["2"]},
        ],
    )
    assert to_change_card(ev, MAPS) is None


def test_normalize_system_changed_by():
    ev = _event(
        id="sys",
        serviceName="PeoplePermissions",
        entityType="Role",
        action="MemberAdd",
        level="SYSTEM",
        user={},
        entity={
            "id": ROLE_ID,
            "name": f"{USER_ID}--{ROLE_ID}--{ORG_ID}",
        },
    )
    card = to_change_card(ev, MAPS)
    assert card["changed_by"]["kind"] == "SYSTEM"


# ---------------------------------------------------------------------------
# Orquestração deep_search / deep_categories
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_user_changes_default_skips_deep(monkeypatch):
    """Sem deep: só Directory; serviços deep marcados omitted."""
    called: list[str] = []

    async def fake_resolve(user_ref):
        return {"id": USER_ID, "name": "Fulano", "email": "f@ex.com"}

    async def fake_maps():
        return MAPS

    async def fake_paginated(**kwargs):
        called.append(kwargs["service_name"])
        return ([], False, 0)

    async def fake_deep(**kwargs):
        called.append(f"deep:{kwargs['service_name']}")
        return ([], False, 0)

    monkeypatch.setattr("services.user_audit.resolve_user", fake_resolve)
    monkeypatch.setattr("services.user_audit.fetch_name_maps", fake_maps)
    monkeypatch.setattr("services.user_audit._paginated_audit", fake_paginated)
    monkeypatch.setattr("services.user_audit._deep_audit_chunked", fake_deep)

    result = await get_user_changes(
        "f@ex.com",
        "2026-07-01T00:00:00Z",
        "2026-07-07T00:00:00Z",
    )
    assert result["meta"]["deep_search"] is False
    assert result["meta"]["deep_categories"] == []
    assert result["meta"]["include_directory"] is True
    assert called == ["Directory"]
    for key in ("Groups", "PeoplePermissions", "ContactCenter"):
        assert result["meta"]["scanned_by_service"][key]["omitted"] is True
        assert result["meta"]["scanned_by_service"][key]["reason"] == "deep_search_off"
    assert result["meta"]["truncated_by_service"]["Directory"] is False


@pytest.mark.asyncio
async def test_get_user_changes_deep_search_compat_runs_all(monkeypatch):
    """deep_search=True (compat): Directory + deep Groups/Role/Queue."""
    called: list[str] = []

    async def fake_resolve(user_ref):
        return {"id": USER_ID, "name": "Fulano", "email": "f@ex.com"}

    async def fake_maps():
        return MAPS

    async def fake_paginated(**kwargs):
        called.append(kwargs["service_name"])
        return ([], False, 0)

    async def fake_deep(**kwargs):
        called.append(f"deep:{kwargs['service_name']}")
        return ([], False, 0)

    monkeypatch.setattr("services.user_audit.resolve_user", fake_resolve)
    monkeypatch.setattr("services.user_audit.fetch_name_maps", fake_maps)
    monkeypatch.setattr("services.user_audit._paginated_audit", fake_paginated)
    monkeypatch.setattr("services.user_audit._deep_audit_window", fake_deep)

    result = await get_user_changes(
        "f@ex.com",
        "2026-07-01T00:00:00Z",
        "2026-07-02T00:00:00Z",
        deep_search=True,
    )
    assert result["meta"]["deep_search"] is True
    assert set(result["meta"]["deep_categories"]) == {"queue", "role", "group"}
    assert result["meta"]["include_directory"] is True
    assert "Directory" in called
    assert "deep:Groups" in called
    assert "deep:PeoplePermissions" in called
    assert "deep:ContactCenter" in called
    for key in ("Groups", "PeoplePermissions", "ContactCenter"):
        assert "omitted" not in result["meta"]["scanned_by_service"][key]


@pytest.mark.asyncio
async def test_get_user_changes_deep_categories_queue_only(monkeypatch):
    """deep_categories=['queue']: só ContactCenter; sem Directory."""
    called: list[str] = []

    async def fake_resolve(user_ref):
        return {"id": USER_ID, "name": "Fulano", "email": "f@ex.com"}

    async def fake_maps():
        return MAPS

    async def fake_paginated(**kwargs):
        called.append(kwargs["service_name"])
        return ([], False, 0)

    async def fake_deep(**kwargs):
        called.append(f"deep:{kwargs['service_name']}")
        return ([], True, 10)  # truncated

    monkeypatch.setattr("services.user_audit.resolve_user", fake_resolve)
    monkeypatch.setattr("services.user_audit.fetch_name_maps", fake_maps)
    monkeypatch.setattr("services.user_audit._paginated_audit", fake_paginated)
    monkeypatch.setattr("services.user_audit._deep_audit_window", fake_deep)

    result = await get_user_changes(
        "f@ex.com",
        "2026-07-01T00:00:00Z",
        "2026-07-02T00:00:00Z",
        deep_categories=["queue"],
    )
    assert result["meta"]["deep_categories"] == ["queue"]
    assert result["meta"]["deep_search"] is True
    assert result["meta"]["include_directory"] is False
    assert called == ["deep:ContactCenter"]
    assert result["meta"]["scanned_by_service"]["Directory"]["omitted"] is True
    assert result["meta"]["scanned_by_service"]["Groups"]["reason"] == "not_requested"
    assert result["meta"]["scanned_by_service"]["PeoplePermissions"]["reason"] == (
        "not_requested"
    )
    assert result["meta"]["truncated"] is True
    assert result["meta"]["truncated_by_service"]["ContactCenter"] is True


@pytest.mark.asyncio
async def test_get_user_changes_deep_rejects_over_48_hours():
    """Deep search rejeita intervalos maiores que 48 horas."""
    with pytest.raises(HTTPException) as exc:
        await get_user_changes(
            "f@ex.com",
            "2026-07-01T00:00:00Z",
            "2026-07-04T00:00:00Z",
            deep_categories=["queue"],
        )
    assert exc.value.status_code == 422
    assert "48" in exc.value.detail


@pytest.mark.asyncio
async def test_get_user_changes_deep_categories_invalid():
    """Categoria inválida → 422."""
    with pytest.raises(HTTPException) as exc:
        await get_user_changes(
            "f@ex.com",
            "2026-07-01T00:00:00Z",
            "2026-07-07T00:00:00Z",
            deep_categories=["fila"],
        )
    assert exc.value.status_code == 422
