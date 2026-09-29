import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from services.user_audit import get_queue_changes

QUEUE_ID = "17584ba9-37f5-4a3d-bbc2-41fd78717178"
USER_ID = "f60111c5-66b3-4748-879c-7e56edccbf25"
SUPERVISOR_ID = "7968f119-42ba-4894-8311-7448857893ff"

MOCK_RAW_EVENT_REMOVE = {
    "id": "e23c9158-77af-4f29-aa8c-971cbc756026",
    "serviceName": "ContactCenter",
    "entityType": "Queue",
    "action": "MemberRemove",
    "level": "USER",
    "eventDate": "2026-07-11T22:53:52Z",
    "entity": {
        "id": QUEUE_ID,
        "name": "WPP_SAC_GOLPES_E_FRAUDES_SSA",
        "selfUri": f"/api/v2/routing/queues/{QUEUE_ID}"
    },
    "user": {
        "id": SUPERVISOR_ID,
        "name": "Supervisor Teste",
        "selfUri": f"/api/v2/users/{SUPERVISOR_ID}"
    },
    "propertyChanges": [
        {
            "property": f"QueueMember/{QUEUE_ID}:{USER_ID}",
            "oldValues": ["<queue member deleted>"],
            "newValues": []
        }
    ],
    "context": {
        "entityId": QUEUE_ID,
        "auditType": "QUEUE"
    }
}

MOCK_RAW_EVENT_DEACTIVATE = {
    "id": "44545a09-65f4-48d2-b625-807ec09257ba",
    "serviceName": "ContactCenter",
    "entityType": "Queue",
    "action": "MemberUpdate",
    "level": "USER",
    "eventDate": "2026-07-11T20:03:27Z",
    "entity": {
        "id": QUEUE_ID,
        "name": "WPP_SAC_GOLPES_E_FRAUDES_SSA",
    },
    "user": {
        "id": SUPERVISOR_ID,
        "name": "Supervisor Teste",
    },
    "propertyChanges": [
        {
            "property": f"QueueMember/{QUEUE_ID}:{USER_ID}:joined",
            "oldValues": ["true"],
            "newValues": ["false"]
        }
    ],
}


@pytest.mark.asyncio
async def test_get_queue_changes_missing_id():
    with pytest.raises(HTTPException) as exc_info:
        await get_queue_changes("", "2026-07-01T00:00:00Z", "2026-07-10T00:00:00Z")
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_get_queue_changes_interval_over_30_days():
    with pytest.raises(HTTPException) as exc_info:
        await get_queue_changes(
            QUEUE_ID, "2026-07-01T00:00:00Z", "2026-08-10T00:00:00Z"
        )
    assert exc_info.value.status_code == 422
    assert "máximo de 30 dias" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_queue_changes_success(monkeypatch):
    async def fake_paginated(**kwargs):
        assert kwargs["service_name"] == "ContactCenter"
        assert {"property": "EntityType", "value": "Queue"} in kwargs["filters"]
        assert {"property": "EntityId", "value": QUEUE_ID} in kwargs["filters"]
        return ([MOCK_RAW_EVENT_REMOVE, MOCK_RAW_EVENT_DEACTIVATE], False, 2)

    async def fake_maps():
        return {
            "queues": {QUEUE_ID: "WPP_SAC_GOLPES_E_FRAUDES_SSA"},
            "roles": {},
            "groups": {},
            "divisions": {},
        }

    async def fake_resolve_user(uid):
        if uid == USER_ID:
            return {"id": USER_ID, "name": "Lorena Bastos", "email": "lorena@corp.caixa.gov.br"}
        return {"id": uid, "name": "Desconhecido", "email": None}

    monkeypatch.setattr("services.user_audit._paginated_audit", fake_paginated)
    monkeypatch.setattr("services.user_audit.fetch_name_maps", fake_maps)
    monkeypatch.setattr("services.user_audit.resolve_user", fake_resolve_user)

    result = await get_queue_changes(
        QUEUE_ID,
        "2026-07-01T00:00:00Z",
        "2026-07-15T00:00:00Z",
    )

    assert result["queue"]["id"] == QUEUE_ID
    assert result["queue"]["name"] == "WPP_SAC_GOLPES_E_FRAUDES_SSA"
    assert len(result["changes"]) == 2

    # Verifica o card de MemberRemove
    card_remove = next(c for c in result["changes"] if c["action"] == "remove")
    assert card_remove["category"] == "queue"
    assert card_remove["before"] == "Membro removido da fila"
    assert card_remove["after"] is None
    assert card_remove["changed_by"]["name"] == "Supervisor Teste"
    assert card_remove["target_user"]["name"] == "Lorena Bastos"

    # Verifica o card de MemberUpdate (inativação)
    card_deact = next(c for c in result["changes"] if c["action"] == "deactivate")
    assert card_deact["category"] == "queue"
    assert card_deact["before"] == "ativo na fila"
    assert card_deact["after"] == "inativo na fila"


@pytest.mark.asyncio
async def test_get_queue_changes_target_user_filter(monkeypatch):
    other_user_id = "00000000-0000-0000-0000-000000000001"
    event_other = dict(MOCK_RAW_EVENT_REMOVE)
    event_other["propertyChanges"] = [
        {
            "property": f"QueueMember/{QUEUE_ID}:{other_user_id}",
            "oldValues": ["<queue member deleted>"],
            "newValues": []
        }
    ]

    async def fake_paginated(**kwargs):
        return ([MOCK_RAW_EVENT_REMOVE, event_other], False, 2)

    async def fake_maps():
        return {
            "queues": {QUEUE_ID: "WPP_SAC_GOLPES_E_FRAUDES_SSA"},
            "roles": {},
            "groups": {},
            "divisions": {},
        }

    async def fake_resolve_user(uid):
        return {"id": uid, "name": f"User {uid[:4]}", "email": f"{uid[:4]}@corp.caixa.gov.br"}

    monkeypatch.setattr("services.user_audit._paginated_audit", fake_paginated)
    monkeypatch.setattr("services.user_audit.fetch_name_maps", fake_maps)
    monkeypatch.setattr("services.user_audit.resolve_user", fake_resolve_user)

    result = await get_queue_changes(
        QUEUE_ID,
        "2026-07-01T00:00:00Z",
        "2026-07-15T00:00:00Z",
        target_user_id=USER_ID
    )

    # Apenas o card do USER_ID deve vir
    assert len(result["changes"]) == 1
    assert result["changes"][0]["target_user"]["id"] == USER_ID


@pytest.mark.asyncio
async def test_get_queue_changes_integration_client_id(monkeypatch):
    from config import settings
    oauth_event = dict(MOCK_RAW_EVENT_REMOVE)
    oauth_event["user"] = {
        "id": settings.GENESYS_CLIENT_ID,
        "name": None,
        "selfUri": f"/api/v2/users/{settings.GENESYS_CLIENT_ID}"
    }

    async def fake_paginated(**kwargs):
        return ([oauth_event], False, 1)

    async def fake_maps():
        return {
            "queues": {QUEUE_ID: "WPP_SAC_GOLPES_E_FRAUDES_SSA"},
            "roles": {},
            "groups": {},
            "divisions": {},
        }

    async def fake_resolve_user(uid):
        return {"id": uid, "name": "Lorena Bastos", "email": "lorena@corp.caixa.gov.br"}

    monkeypatch.setattr("services.user_audit._paginated_audit", fake_paginated)
    monkeypatch.setattr("services.user_audit.fetch_name_maps", fake_maps)
    monkeypatch.setattr("services.user_audit.resolve_user", fake_resolve_user)

    result = await get_queue_changes(
        QUEUE_ID,
        "2026-07-01T00:00:00Z",
        "2026-07-15T00:00:00Z",
    )

    card = result["changes"][0]
    assert card["changed_by"]["kind"] == "INTEGRATION"
    assert card["changed_by"]["name"] == "Genesys Manager (Integração)"
