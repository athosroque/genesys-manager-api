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


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = _fake_user_dep
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_uuid_regex():
    assert UUID_REGEX.match("a157b2f2-9a3f-4426-b7cf-b1a040594b28")
    assert UUID_REGEX.match("{a157b2f2-9a3f-4426-b7cf-b1a040594b28}") is None  # Regex pura nao stripa
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

            # Testa com chaves para validar a sanitização
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

            response = client.get("/users/{a157b2f2-9a3f-4426-b7cf-b1a040594b28}/queues")

            assert response.status_code == 200
            assert len(response.json()["queues"]) == 1
            assert response.json()["queues"][0]["name"] == "Queue 1"


@pytest.mark.asyncio
async def test_get_user_name_success():
    with patch("routes.users.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "u1", "name": "Fulano"}
            mock_get.return_value = mock_response
            response = client.get("/users/{u1}/name")
            assert response.status_code == 200
            assert response.json() == {"found": True, "id": "u1", "name": "Fulano"}


@pytest.mark.asyncio
async def test_get_user_name_not_found():
    with patch("routes.users.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            response = client.get("/users/u-missing/name")
            assert response.status_code == 200
            assert response.json() == {"found": False, "id": "u-missing", "name": None}


def test_get_user_name_requires_auth():
    app.dependency_overrides.pop(get_current_user, None)
    response = client.get("/users/u1/name")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Testes do Diagnóstico de Telefonia / Ramal (WebRTC)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_telephony_scenario_1_healthy():
    """Cenário 1: Estação atribuída, ASSOCIATED, telefone ativo com Site."""
    mock_user = {
        "id": "u-ok",
        "name": "Usuario Saudavel",
        "email": "saudavel@exemplo.com",
        "station": {
            "effectiveStation": {
                "id": "st-123",
                "name": "p523303_1",
                "providerInfo": {"name": "p523303_1"}
            }
        }
    }
    mock_station = {
        "id": "st-123",
        "name": "p523303_SIP",
        "status": "ASSOCIATED",
        "type": "generic_sip",
        "lineAppearanceId": "line-01"
    }
    mock_phone = {
        "entities": [
            {
                "id": "ph-123",
                "name": "p523303_SIP",
                "state": "active",
                "site": {"id": "site-1", "name": "Site Central"},
                "phoneBaseSettings": {"id": "pbs-1", "name": "Padrao WebRTC"}
            }
        ]
    }

    async def fake_get(url, headers=None):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        if "/users/u-ok" in url:
            resp.json.return_value = mock_user
        elif "/stations/st-123" in url:
            resp.json.return_value = mock_station
        elif "lines.id=st-123" in url or "webRtcUser.id=u-ok" in url:
            resp.json.return_value = mock_phone
        else:
            resp.status_code = 404
            resp.json.return_value = {}
        return resp

    with patch("routes.users.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        with patch("httpx.AsyncClient.get", side_effect=fake_get):
            response = client.get("/users/{u-ok}/telephony")
            assert response.status_code == 200
            data = response.json()
            assert data["scenario"] == 1
            assert data["is_healthy"] is True
            assert data["station"]["id"] == "st-123"
            assert data["station"]["status"] == "ASSOCIATED"
            assert data["station"]["is_associated"] is True
            assert data["phone"]["id"] == "ph-123"
            assert data["phone"]["state"] == "active"
            assert data["phone"]["site"]["name"] == "Site Central"
            assert len(data["issues"]) == 0
            assert len(data["recommendations"]) > 0


@pytest.mark.asyncio
async def test_get_user_telephony_scenario_2_no_station():
    """Cenário 2: Usuário sem estação atribuída (effectiveStation nula/vazia)."""
    mock_user = {
        "id": "u-no-st",
        "name": "Usuario Sem Estacao",
        "email": "semestacao@exemplo.com",
        "station": {}
    }

    async def fake_get(url, headers=None):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        if "/users/u-no-st" in url:
            resp.json.return_value = mock_user
        elif "phones" in url:
            resp.json.return_value = {"entities": []}
        else:
            resp.status_code = 404
            resp.json.return_value = {}
        return resp

    with patch("routes.users.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        with patch("httpx.AsyncClient.get", side_effect=fake_get):
            response = client.get("/users/{u-no-st}/telephony")
            assert response.status_code == 200
            data = response.json()
            assert data["scenario"] == 2
            assert data["is_healthy"] is False
            assert data["summary"]["station_assigned"] is False
            assert data["station"] is None
            assert any("não possui estação efetiva atribuída" in issue for issue in data["issues"])


@pytest.mark.asyncio
async def test_get_user_telephony_scenario_2_disassociated_station():
    """Cenário 2: Usuário com estação DISASSOCIATED."""
    mock_user = {
        "id": "u-disassoc",
        "name": "Usuario Desconectado",
        "email": "desconectado@exemplo.com",
        "station": {
            "effectiveStation": {
                "id": "st-dis",
                "name": "p999999_1",
                "providerInfo": {"name": "p999999_1"}
            }
        }
    }
    mock_station = {
        "id": "st-dis",
        "name": "p999999_SIP",
        "status": "DISASSOCIATED",
        "type": "generic_sip",
        "lineAppearanceId": "line-02"
    }
    mock_phone = {
        "entities": [
            {
                "id": "ph-dis",
                "name": "p999999_SIP",
                "state": "active",
                "site": {"id": "site-1", "name": "Site Central"}
            }
        ]
    }

    async def fake_get(url, headers=None):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        if "/users/u-disassoc" in url:
            resp.json.return_value = mock_user
        elif "/stations/st-dis" in url:
            resp.json.return_value = mock_station
        elif "lines.id=st-dis" in url:
            resp.json.return_value = mock_phone
        else:
            resp.status_code = 404
            resp.json.return_value = {}
        return resp

    with patch("routes.users.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        with patch("httpx.AsyncClient.get", side_effect=fake_get):
            response = client.get("/users/u-disassoc/telephony")
            assert response.status_code == 200
            data = response.json()
            assert data["scenario"] == 2
            assert data["is_healthy"] is False
            assert data["summary"]["station_associated"] is False
            assert data["station"]["status"] == "DISASSOCIATED"
            assert any("Estação não está associada" in issue for issue in data["issues"])


def test_get_user_telephony_requires_auth():
    app.dependency_overrides.pop(get_current_user, None)
    response = client.get("/users/u1/telephony")
    assert response.status_code == 401
