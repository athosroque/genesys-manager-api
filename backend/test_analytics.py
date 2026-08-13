"""Testes do módulo de analytics de presença."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from auth_local import get_current_user
from main import app
from routes.analytics import MAX_RETRIES, genesys_request
from services.user_presence import (
    build_presence_response,
    interval_for_br_date,
    parse_primary_presence,
    validate_presence_date,
)


def _fake_user():
    return {"username": "tester", "active": True}


def _resp(status_code, payload=None, headers=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = payload or {}
    r.text = str(payload or {})
    r.headers = headers or {}
    return r


# ---------------------------------------------------------------------------
# Helpers de intervalo / parse
# ---------------------------------------------------------------------------
def test_interval_for_br_date_august_2026_is_minus_03():
    """Ago/2026 sem horário de verão → meia-noite BR = 03:00Z."""
    assert interval_for_br_date(date(2026, 8, 5)) == (
        "2026-08-05T03:00:00Z/2026-08-06T03:00:00Z"
    )


def test_interval_for_br_date_january_also_minus_03():
    """BR não observa DST desde 2019 — jan/2026 também −03."""
    assert interval_for_br_date(date(2026, 1, 15)) == (
        "2026-01-15T03:00:00Z/2026-01-16T03:00:00Z"
    )


def test_validate_presence_date_rejects_future():
    now = datetime(2026, 8, 5, 18, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="futura"):
        validate_presence_date(date(2026, 8, 6), now=now)


def test_validate_presence_date_rejects_too_old():
    now = datetime(2026, 8, 5, 18, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="histórico"):
        validate_presence_date(date(2020, 1, 1), now=now)


def test_validate_presence_date_accepts_today_br():
    # 2026-08-05 02:00 UTC ainda é 2026-08-04 em São Paulo (−03)
    now = datetime(2026, 8, 5, 2, 0, tzinfo=timezone.utc)
    validate_presence_date(date(2026, 8, 4), now=now)


def test_parse_primary_presence_with_end_times():
    payload = {
        "userDetails": [
            {
                "userId": "u1",
                "primaryPresence": [
                    {
                        "startTime": "2026-08-05T12:00:00.000Z",
                        "endTime": "2026-08-05T14:20:00.000Z",
                        "systemPresence": "AVAILABLE",
                        "organizationPresenceId": "org-1",
                    },
                    {
                        "startTime": "2026-08-05T14:20:00.000Z",
                        "endTime": "2026-08-05T14:55:00.000Z",
                        "systemPresence": "BUSY",
                    },
                ],
            }
        ]
    }
    parsed = parse_primary_presence(payload)
    assert parsed["empty"] is False
    assert parsed["open_segment"] is False
    assert len(parsed["segments"]) == 2
    assert parsed["segments"][0]["system_presence"] == "AVAILABLE"
    assert parsed["segments"][0]["duration_minutes"] == 140.0
    assert parsed["segments"][0]["is_open"] is False
    assert parsed["segments"][0]["start"].endswith("-03:00")
    assert parsed["totals_minutes"]["AVAILABLE"] == 140.0
    assert parsed["totals_minutes"]["BUSY"] == 35.0
    assert parsed["totals_minutes"]["OFFLINE"] == 0.0


def test_parse_primary_presence_missing_end_uses_now():
    payload = {
        "userDetails": [
            {
                "primaryPresence": [
                    {
                        "startTime": "2026-08-05T12:00:00Z",
                        "systemPresence": "AVAILABLE",
                    }
                ]
            }
        ]
    }
    now = datetime(2026, 8, 5, 13, 30, tzinfo=timezone.utc)
    parsed = parse_primary_presence(payload, now=now)
    assert parsed["open_segment"] is True
    assert parsed["segments"][0]["is_open"] is True
    assert parsed["segments"][0]["duration_minutes"] == 90.0
    assert parsed["totals_minutes"]["AVAILABLE"] == 90.0


def test_parse_primary_presence_empty_payload():
    parsed = parse_primary_presence({"userDetails": []})
    assert parsed["empty"] is True
    assert parsed["segments"] == []
    assert parsed["totals_minutes"] == {}
    assert parsed["total_tracked_minutes"] == 0.0


def test_parse_skips_segment_without_start():
    payload = {
        "userDetails": [
            {
                "primaryPresence": [
                    {"endTime": "2026-08-05T14:00:00Z", "systemPresence": "BUSY"},
                    {
                        "startTime": "2026-08-05T14:00:00Z",
                        "endTime": "2026-08-05T15:00:00Z",
                        "systemPresence": "AWAY",
                    },
                ]
            }
        ]
    }
    parsed = parse_primary_presence(payload)
    assert len(parsed["segments"]) == 1
    assert parsed["segments"][0]["system_presence"] == "AWAY"


def test_build_presence_response_shape():
    now = datetime(2026, 8, 5, 18, 30, tzinfo=timezone.utc)
    result = build_presence_response(
        user_id="00403044-6669-4c41-bc1e-f1dd8f2ee61e",
        day=date(2026, 8, 5),
        payload={"userDetails": []},
        now=now,
    )
    assert result["user_id"] == "00403044-6669-4c41-bc1e-f1dd8f2ee61e"
    assert result["date"] == "2026-08-05"
    assert result["timezone"] == "America/Sao_Paulo"
    assert result["interval"] == "2026-08-05T03:00:00Z/2026-08-06T03:00:00Z"
    assert result["queried_at"] == "2026-08-05T18:30:00Z"
    assert result["empty"] is True


def test_parse_clamps_segment_crossing_midnight_to_day():
    """OFFLINE começando dia anterior e terminando depois não pode estourar 24h."""
    # 2026-08-03 10:59 BR = 13:59Z; 2026-08-05 10:00 BR = 13:00Z → ~47h brutos
    payload = {
        "userDetails": [
            {
                "primaryPresence": [
                    {
                        "startTime": "2026-08-03T13:59:00Z",
                        "endTime": "2026-08-05T13:00:00Z",
                        "systemPresence": "OFFLINE",
                    }
                ]
            }
        ]
    }
    parsed = parse_primary_presence(
        payload,
        day=date(2026, 8, 4),
        now=datetime(2026, 8, 5, 18, 0, tzinfo=timezone.utc),
    )
    assert len(parsed["segments"]) == 1
    seg = parsed["segments"][0]
    assert seg["is_open"] is False
    assert seg["duration_minutes"] == 1440.0
    assert seg["start"].startswith("2026-08-04T00:00:00")
    assert seg["end"].startswith("2026-08-05T00:00:00")
    assert parsed["totals_minutes"]["OFFLINE"] == 1440.0


def test_parse_open_segment_on_past_day_closes_at_midnight():
    payload = {
        "userDetails": [
            {
                "primaryPresence": [
                    {
                        "startTime": "2026-08-04T15:00:00Z",  # 12:00 BR
                        "systemPresence": "AVAILABLE",
                    }
                ]
            }
        ]
    }
    parsed = parse_primary_presence(
        payload,
        day=date(2026, 8, 4),
        now=datetime(2026, 8, 5, 18, 0, tzinfo=timezone.utc),
    )
    assert len(parsed["segments"]) == 1
    seg = parsed["segments"][0]
    assert seg["is_open"] is False
    assert seg["duration_minutes"] == 720.0  # 12:00 → 24:00
    assert parsed["open_segment"] is False


def test_build_presence_response_clamps_via_day():
    now = datetime(2026, 8, 5, 18, 30, tzinfo=timezone.utc)
    payload = {
        "userDetails": [
            {
                "primaryPresence": [
                    {
                        "startTime": "2026-08-03T13:59:00Z",
                        "endTime": "2026-08-05T13:00:00Z",
                        "systemPresence": "OFFLINE",
                    }
                ]
            }
        ]
    }
    result = build_presence_response(
        user_id="u1",
        day=date(2026, 8, 5),
        payload=payload,
        now=now,
    )
    assert result["empty"] is False
    assert len(result["segments"]) == 1
    # 00:00 BR → 10:00 BR em 2026-08-05
    assert result["segments"][0]["duration_minutes"] == 600.0
    assert result["segments"][0]["duration_minutes"] <= 1440.0


# ---------------------------------------------------------------------------
# genesys_request (retry / 403)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_genesys_request_retries_429_then_succeeds():
    with patch("routes.analytics.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        with patch("routes.analytics.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
                mock_req.side_effect = [
                    _resp(
                        429,
                        {
                            "message": "Rate limit exceeded. Retry the request in [3] seconds"
                        },
                    ),
                    _resp(200, {"userDetails": []}),
                ]
                result = await genesys_request(
                    "POST", "/analytics/users/details/query", json={}
                )
                assert result == {"userDetails": []}
                assert mock_req.call_count == 2
                mock_sleep.assert_awaited_once_with(3.0)


@pytest.mark.asyncio
async def test_genesys_request_gives_up_after_max_retries():
    with patch("routes.analytics.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        with patch("routes.analytics.asyncio.sleep", new_callable=AsyncMock):
            with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = _resp(
                    429, {"message": "Retry the request in [1] seconds"}
                )
                with pytest.raises(Exception) as exc_info:
                    await genesys_request("POST", "/analytics/users/details/query")
                assert getattr(exc_info.value, "status_code", None) == 429
                assert mock_req.call_count == MAX_RETRIES + 1


@pytest.mark.asyncio
async def test_genesys_request_403_mentions_analytics_scope():
    with patch("routes.analytics.get_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "fake_token"
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _resp(403, {"message": "forbidden"})
            with pytest.raises(Exception) as exc_info:
                await genesys_request("POST", "/analytics/users/details/query")
            assert getattr(exc_info.value, "status_code", None) == 403
            assert "analytics:readonly" in str(exc_info.value.detail)
            assert mock_req.call_count == 1


# ---------------------------------------------------------------------------
# Endpoint HTTP
# ---------------------------------------------------------------------------
def test_presence_endpoint_success():
    app.dependency_overrides[get_current_user] = _fake_user
    genesys_payload = {
        "userDetails": [
            {
                "userId": "a157b2f2-9a3f-4426-b7cf-b1a040594b28",
                "primaryPresence": [
                    {
                        "startTime": "2026-08-05T12:00:00Z",
                        "endTime": "2026-08-05T13:00:00Z",
                        "systemPresence": "AVAILABLE",
                    }
                ],
            }
        ]
    }
    try:
        with patch(
            "routes.analytics.genesys_request", new_callable=AsyncMock
        ) as mock_gx:
            mock_gx.return_value = genesys_payload
            client = TestClient(app)
            response = client.get(
                "/analytics/users/{a157b2f2-9a3f-4426-b7cf-b1a040594b28}/presence"
                "?date=2026-08-05"
            )
            assert response.status_code == 200
            body = response.json()
            assert body["user_id"] == "a157b2f2-9a3f-4426-b7cf-b1a040594b28"
            assert body["date"] == "2026-08-05"
            assert body["empty"] is False
            assert body["totals_minutes"]["AVAILABLE"] == 60.0
            assert len(body["segments"]) == 1

            call_kwargs = mock_gx.await_args
            assert call_kwargs.args[0] == "POST"
            assert call_kwargs.args[1] == "/analytics/users/details/query"
            sent = call_kwargs.kwargs["json"]
            assert sent["interval"] == "2026-08-05T03:00:00Z/2026-08-06T03:00:00Z"
            assert (
                sent["userFilters"][0]["predicates"][0]["value"]
                == "a157b2f2-9a3f-4426-b7cf-b1a040594b28"
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_presence_endpoint_empty_result():
    app.dependency_overrides[get_current_user] = _fake_user
    try:
        with patch(
            "routes.analytics.genesys_request", new_callable=AsyncMock
        ) as mock_gx:
            mock_gx.return_value = {"userDetails": []}
            client = TestClient(app)
            response = client.get(
                "/analytics/users/a157b2f2-9a3f-4426-b7cf-b1a040594b28/presence"
                "?date=2026-08-05"
            )
            assert response.status_code == 200
            body = response.json()
            assert body["empty"] is True
            assert body["segments"] == []
            assert body["totals_minutes"] == {}
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_presence_endpoint_rejects_future_date():
    app.dependency_overrides[get_current_user] = _fake_user
    try:
        client = TestClient(app)
        with patch(
            "routes.analytics.validate_presence_date",
            side_effect=ValueError("Data futura não permitida."),
        ):
            response = client.get(
                "/analytics/users/a157b2f2-9a3f-4426-b7cf-b1a040594b28/presence"
                "?date=2099-01-01"
            )
            assert response.status_code == 422
            assert "futura" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_presence_endpoint_rejects_invalid_uuid():
    app.dependency_overrides[get_current_user] = _fake_user
    try:
        client = TestClient(app)
        response = client.get(
            "/analytics/users/not-a-uuid/presence?date=2026-08-05"
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_presence_endpoint_requires_auth():
    client = TestClient(app)
    response = client.get(
        "/analytics/users/a157b2f2-9a3f-4426-b7cf-b1a040594b28/presence"
        "?date=2026-08-05"
    )
    assert response.status_code in (401, 403)
