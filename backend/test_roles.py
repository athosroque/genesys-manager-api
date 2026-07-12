import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from auth_local import get_current_user

client = TestClient(app)


def _fake_user():
    return {"username": "tester", "active": True}


def _resp(status_code, payload=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = payload or {}
    r.text = ""
    return r


@pytest.mark.asyncio
async def test_list_roles_success():
    app.dependency_overrides[get_current_user] = _fake_user
    try:
        with patch("routes.roles.get_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "fake_token"
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = _resp(200, {
                    "entities": [
                        {"id": "r1", "name": "Admin"},
                        {"id": "r2", "name": "Agent"},
                    ],
                    "pageCount": 1,
                })
                response = client.get("/roles")
                assert response.status_code == 200
                body = response.json()
                assert body["roles"] == [
                    {"id": "r1", "name": "Admin"},
                    {"id": "r2", "name": "Agent"},
                ]
                assert body["truncated"] is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_roles_pagination():
    app.dependency_overrides[get_current_user] = _fake_user
    try:
        with patch("routes.roles.get_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "fake_token"
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                def side_effect(url, *args, **kwargs):
                    if "pageNumber=1" in url:
                        return _resp(200, {"entities": [{"id": "r1", "name": "Admin"}], "pageCount": 2})
                    return _resp(200, {"entities": [{"id": "r2", "name": "Agent"}], "pageCount": 2})
                mock_get.side_effect = side_effect
                response = client.get("/roles")
                assert response.status_code == 200
                assert [r["id"] for r in response.json()["roles"]] == ["r1", "r2"]
                assert mock_get.call_count == 2
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_roles_403_degrades_gracefully():
    app.dependency_overrides[get_current_user] = _fake_user
    try:
        with patch("routes.roles.get_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "fake_token"
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = _resp(403, {})
                response = client.get("/roles")
                assert response.status_code == 200
                body = response.json()
                assert body["roles"] == []
                assert "warning" in body
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_list_roles_requires_auth():
    # Sem override e sem cookie → 401 (dependência get_current_user ativa)
    response = client.get("/roles")
    assert response.status_code == 401
