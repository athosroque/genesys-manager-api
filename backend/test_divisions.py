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
async def test_list_divisions_success():
    app.dependency_overrides[get_current_user] = _fake_user
    try:
        with patch("routes.divisions.get_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "fake_token"
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = _resp(200, {
                    "entities": [
                        {"id": "d1", "name": "CAIXA"},
                        {"id": "d2", "name": "CEATI"},
                    ],
                    "pageCount": 1,
                })
                response = client.get("/divisions")
                assert response.status_code == 200
                body = response.json()
                assert body["divisions"] == [
                    {"id": "d1", "name": "CAIXA"},
                    {"id": "d2", "name": "CEATI"},
                ]
                assert body["truncated"] is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_divisions_pagination():
    app.dependency_overrides[get_current_user] = _fake_user
    try:
        with patch("routes.divisions.get_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "fake_token"
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                def side_effect(url, *args, **kwargs):
                    if "pageNumber=1" in url:
                        return _resp(200, {"entities": [{"id": "d1", "name": "A"}], "pageCount": 2})
                    return _resp(200, {"entities": [{"id": "d2", "name": "B"}], "pageCount": 2})
                mock_get.side_effect = side_effect
                response = client.get("/divisions")
                assert response.status_code == 200
                assert [d["id"] for d in response.json()["divisions"]] == ["d1", "d2"]
                assert mock_get.call_count == 2
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_divisions_403_degrades_gracefully():
    app.dependency_overrides[get_current_user] = _fake_user
    try:
        with patch("routes.divisions.get_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "fake_token"
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = _resp(403, {})
                response = client.get("/divisions")
                assert response.status_code == 200
                body = response.json()
                assert body["divisions"] == []
                assert "warning" in body
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_list_divisions_requires_auth():
    response = client.get("/divisions")
    assert response.status_code == 401
