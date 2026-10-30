import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from main import app
from auth_local import get_current_user
import pytest

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: {"username": "tester", "active": True}
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _resp(status, body=None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.json.return_value = body or {}
    resp.text = ""
    return resp


def test_search_phones_wraps_term_and_maps_results():
    body = {"entities": [{
        "id": "ph-1", "name": "p523303_SIP", "state": "active",
        "site": {"id": "s-1", "name": "Matriz"},
        "webRtcUser": {"id": "u-1", "name": "Fulano"},
    }]}
    with patch("routes.telephony.get_token", new_callable=AsyncMock, return_value="t"), \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_resp(200, body)) as mock_get:
        r = client.get("/telephony/phones/search?name=p523303")
    assert r.status_code == 200
    assert mock_get.call_args.kwargs["params"]["name"] == "*p523303*"
    res = r.json()["results"][0]
    assert res["id"] == "ph-1"
    assert res["web_rtc_user"]["name"] == "Fulano"
    assert res["site"]["name"] == "Matriz"


def test_search_phones_requires_min_length():
    assert client.get("/telephony/phones/search?name=a").status_code == 422


def test_delete_phone_success():
    with patch("routes.telephony.get_token", new_callable=AsyncMock, return_value="t"), \
         patch("httpx.AsyncClient.delete", new_callable=AsyncMock, return_value=_resp(204)) as mock_del:
        r = client.delete("/telephony/phones/{ph-1}")
    assert r.status_code == 200
    assert r.json() == {"success": True, "status": "deleted", "phone_id": "ph-1"}
    assert mock_del.call_args.args[0].endswith("/telephony/providers/edges/phones/ph-1")


@pytest.mark.parametrize("status", [403, 404, 500])
def test_delete_phone_errors_propagate(status):
    with patch("routes.telephony.get_token", new_callable=AsyncMock, return_value="t"), \
         patch("httpx.AsyncClient.delete", new_callable=AsyncMock, return_value=_resp(status)):
        r = client.delete("/telephony/phones/ph-x")
    assert r.status_code == status


def test_routes_require_auth():
    app.dependency_overrides.pop(get_current_user, None)
    assert client.delete("/telephony/phones/ph-1").status_code == 401
