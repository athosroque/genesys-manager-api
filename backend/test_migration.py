import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
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
    resp.text = "erro"
    return resp


def _diagnosis(phone=None):
    return {"phone": phone}


def _reset(body, diagnosis, post_status=200, delete_status=204):
    with patch("routes.migration.get_token", new_callable=AsyncMock, return_value="t"), \
         patch("routes.migration.get_user_telephony_diagnosis", new_callable=AsyncMock, return_value=diagnosis), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=_resp(post_status)) as mock_post, \
         patch("httpx.AsyncClient.delete", new_callable=AsyncMock, return_value=_resp(delete_status)) as mock_del:
        r = client.post("/migration/reset-autoconfig", json=body)
    return r, mock_post, mock_del


def _assert_only_division_and_role(mock_post):
    urls = [c.args[0] for c in mock_post.call_args_list]
    assert len(urls) == 2
    assert "/authorization/divisions/" in urls[0] and urls[0].endswith("/objects/USER")
    assert urls[1].endswith("/bulkadd")


def test_reset_deletes_confirmed_phone():
    r, mock_post, mock_del = _reset(
        {"user_id": "{u-1}", "phone_id": "ph-1"},
        _diagnosis({"id": "ph-1", "name": "p523303_SIP"}),
    )
    assert r.status_code == 200
    _assert_only_division_and_role(mock_post)
    assert mock_del.call_count == 1
    assert mock_del.call_args.args[0].endswith("/telephony/providers/edges/phones/ph-1")
    steps = r.json()["steps"]
    assert [s["status"] for s in steps] == ["ok", "ok", "ok"]
    assert "p523303_SIP" in steps[2]["detail"]


def test_reset_without_phone_only_assigns_division_and_role():
    r, mock_post, mock_del = _reset({"user_id": "u-1"}, _diagnosis(None))
    assert r.status_code == 200
    _assert_only_division_and_role(mock_post)
    mock_del.assert_not_called()
    last = r.json()["steps"][-1]
    assert last["status"] == "skip"
    assert "nenhum ramal foi excluído" in last["detail"]


def test_reset_without_confirmed_phone_never_deletes_new_phone():
    r, _, mock_del = _reset({"user_id": "u-1"}, _diagnosis({"id": "ph-novo", "name": "novo"}))
    assert r.status_code == 200
    mock_del.assert_not_called()
    assert r.json()["steps"][-1]["status"] == "skip"


def test_reset_skips_delete_when_phone_changed():
    r, _, mock_del = _reset(
        {"user_id": "u-1", "phone_id": "ph-1"},
        _diagnosis({"id": "ph-2", "name": "outro"}),
    )
    assert r.status_code == 200
    mock_del.assert_not_called()
    assert r.json()["steps"][-1]["status"] == "skip"


def test_reset_reports_delete_permission_error():
    r, _, _ = _reset(
        {"user_id": "u-1", "phone_id": "ph-1"},
        _diagnosis({"id": "ph-1", "name": "x"}),
        delete_status=403,
    )
    last = r.json()["steps"][-1]
    assert last["status"] == "error"
    assert "telephony:plugin:all" in last["detail"]


def test_reset_aborts_before_changes_when_user_not_found():
    with patch("routes.migration.get_token", new_callable=AsyncMock, return_value="t"), \
         patch("routes.migration.get_user_telephony_diagnosis", new_callable=AsyncMock,
               side_effect=HTTPException(status_code=404, detail="nao encontrado")), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("httpx.AsyncClient.delete", new_callable=AsyncMock) as mock_del:
        r = client.post("/migration/reset-autoconfig", json={"user_id": "u-x", "phone_id": "ph-1"})
    assert r.status_code == 404
    mock_post.assert_not_called()
    mock_del.assert_not_called()


def test_run_migration_mode_1_still_assigns_division_and_role():
    with patch("routes.migration.get_token", new_callable=AsyncMock, return_value="t"), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=_resp(200)) as mock_post:
        r = client.post("/migration/run", json={"user_id": "u-1", "op": "1"})
    assert r.status_code == 200
    _assert_only_division_and_role(mock_post)
    assert [s["label"] for s in r.json()["steps"]] == ["Mover para Divisão Home", "Atribuir Role"]


def test_reset_requires_auth():
    app.dependency_overrides.pop(get_current_user, None)
    assert client.post("/migration/reset-autoconfig", json={"user_id": "u-1"}).status_code == 401
