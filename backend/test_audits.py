import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from auth_local import get_current_user
from routes.audits import genesys_request, MAX_RETRIES


def _fake_user():
    return {"username": "tester", "active": True}


def _resp(status_code, payload=None, headers=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = payload or {}
    r.text = str(payload or {})
    r.headers = headers or {}
    return r


@pytest.mark.asyncio
async def test_genesys_request_retries_429_then_succeeds():
    with patch("routes.audits.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        with patch("routes.audits.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
                mock_req.side_effect = [
                    _resp(429, {"message": "Rate limit exceeded the maximum. Retry the request in [3] seconds"}),
                    _resp(200, {"ok": True}),
                ]
                result = await genesys_request("GET", "/audits/query/servicemapping")
                assert result == {"ok": True}
                assert mock_req.call_count == 2
                mock_sleep.assert_awaited_once_with(3.0)


@pytest.mark.asyncio
async def test_genesys_request_respects_retry_after_header():
    with patch("routes.audits.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        with patch("routes.audits.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
                mock_req.side_effect = [
                    _resp(429, {"message": "no bracket here"}, headers={"Retry-After": "5"}),
                    _resp(200, {"ok": True}),
                ]
                result = await genesys_request("GET", "/audits/query/servicemapping")
                assert result == {"ok": True}
                mock_sleep.assert_awaited_once_with(5.0)


@pytest.mark.asyncio
async def test_genesys_request_gives_up_after_max_retries():
    with patch("routes.audits.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        with patch("routes.audits.asyncio.sleep", new_callable=AsyncMock):
            with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = _resp(429, {"message": "Retry the request in [1] seconds"})
                with pytest.raises(Exception) as exc_info:
                    await genesys_request("GET", "/audits/query/servicemapping")
                assert "429" in str(exc_info.value) or getattr(exc_info.value, "status_code", None) == 429
                # 1 tentativa inicial + MAX_RETRIES novas tentativas
                assert mock_req.call_count == MAX_RETRIES + 1


@pytest.mark.asyncio
async def test_genesys_request_403_no_retry():
    with patch("routes.audits.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _resp(403, {"message": "forbidden"})
            with pytest.raises(Exception):
                await genesys_request("GET", "/audits/query/servicemapping")
            assert mock_req.call_count == 1


@pytest.mark.asyncio
async def test_deep_search_forwards_custom_page_size():
    """
    deep_search_audits() mandava pageSize=100 fixo pra Genesys, ignorando
    body.page_size (bug corrigido) — este teste trava a regressão.
    """
    app.dependency_overrides[get_current_user] = _fake_user
    try:
        with patch("routes.audits.get_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "fake_token"
            with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
                mock_req.side_effect = [
                    _resp(200, {"id": "tid1", "state": "Succeeded"}),  # POST /audits/query
                    _resp(200, {"entities": [], "cursor": None}),  # GET .../results
                ]
                client = TestClient(app)
                response = client.post(
                    "/audits/search/deep",
                    json={
                        "interval_start": "2026-01-01T00:00:00Z",
                        "interval_end": "2026-01-02T00:00:00Z",
                        "service_name": "PeoplePermissions",
                        "match_value": "u1",
                        "page_size": 250,
                        "max_pages": 3,
                    },
                )
                assert response.status_code == 200
                # 2ª chamada = GET .../results — confere o pageSize enviado à Genesys
                _, results_kwargs = mock_req.call_args_list[1]
                assert results_kwargs["params"]["pageSize"] == 250
    finally:
        app.dependency_overrides.pop(get_current_user, None)
