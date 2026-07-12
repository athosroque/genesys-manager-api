import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from routes.users import UUID_REGEX
from auth_local import get_current_user

client = TestClient(app)


def _fake_user_dep():
    return {"username": "tester", "active": True}

def test_uuid_regex():
    assert UUID_REGEX.match("a157b2f2-9a3f-4426-b7cf-b1a040594b28")
    assert UUID_REGEX.match("{a157b2f2-9a3f-4426-b7cf-b1a040594b28}") is None # Regex pura nao stripa
    assert not UUID_REGEX.match("not-a-uuid")

@pytest.mark.asyncio
async def test_search_user_by_uuid_success():
    mock_user = {"id": "123", "name": "Test User", "email": "test@corp.caixa.gov.br"}
    
    with patch("auth.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_user
            mock_get.return_value = mock_response
            
            # Testa com chaves para validar a sanitização que acabamos de fazer
            response = client.get("/users/search?q={a157b2f2-9a3f-4426-b7cf-b1a040594b28}")
            
            assert response.status_code == 200
            assert response.json() == {"found": True, "user": mock_user}

@pytest.mark.asyncio
async def test_search_user_by_email_success():
    mock_results = {"results": [{"id": "123", "email": "user@corp.caixa.gov.br"}]}
    
    with patch("auth.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_results
            mock_post.return_value = mock_response
            
            # Busca por matrícula
            response = client.get("/users/search?q=c108514")
            
            assert response.status_code == 200
            assert response.json()["found"] is True
            assert response.json()["user"]["id"] == "123"

@pytest.mark.asyncio
async def test_get_user_queues_sanitization():
    mock_queues = {"entities": [{"id": "q1", "name": "Queue 1", "joined": True}]}
    
    with patch("auth.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_queues
            mock_get.return_value = mock_response
            
            # Testa sanitização no path parameter
            response = client.get("/users/{a157b2f2-9a3f-4426-b7cf-b1a040594b28}/queues")

            assert response.status_code == 200
            assert len(response.json()["queues"]) == 1
            assert response.json()["queues"][0]["name"] == "Queue 1"


@pytest.mark.asyncio
async def test_get_user_name_success():
    app.dependency_overrides[get_current_user] = _fake_user_dep
    try:
        with patch("routes.users.get_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "fake_token"
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"id": "u1", "name": "Fulano"}
                mock_get.return_value = mock_response
                # Braces validam a sanitização do path param
                response = client.get("/users/{u1}/name")
                assert response.status_code == 200
                assert response.json() == {"found": True, "id": "u1", "name": "Fulano"}
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_user_name_not_found():
    app.dependency_overrides[get_current_user] = _fake_user_dep
    try:
        with patch("routes.users.get_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "fake_token"
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 404
                mock_get.return_value = mock_response
                response = client.get("/users/u-missing/name")
                assert response.status_code == 200
                assert response.json() == {"found": False, "id": "u-missing", "name": None}
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_get_user_name_requires_auth():
    # Sem override e sem cookie → 401
    response = client.get("/users/u1/name")
    assert response.status_code == 401
