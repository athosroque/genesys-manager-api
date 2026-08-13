"""
Analytics de presença — Genesys Cloud User Status Detail
========================================================

Endpoint exposto ao frontend:

  GET /analytics/users/{user_id}/presence?date=YYYY-MM-DD
      Consulta o histórico de primaryPresence de um usuário no dia civil
      America/Sao_Paulo via POST {BASE_URL}/analytics/users/details/query.

OAuth scope necessário no client credentials: analytics:readonly
(role da integração com permissão de analytics user detail nas divisões).
"""

from __future__ import annotations

import asyncio
import re
from datetime import date
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from auth import get_token, h
from auth_local import get_current_user
from config import BASE_URL
from services.user_presence import (
    build_presence_response,
    interval_for_br_date,
    validate_presence_date,
)

router = APIRouter()

UUID_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

MAX_RETRIES = 5
DEFAULT_RETRY_SECONDS = 2.0
# Analytics síncrono: timeout típico da família ~10s; folga generosa.
HTTP_TIMEOUT = 30.0


def _retry_after_seconds(resp: httpx.Response) -> float:
    """Extrai o tempo de espera sugerido pela Genesys num 429."""
    header = resp.headers.get("Retry-After")
    if header:
        try:
            return max(float(header), 0.5)
        except ValueError:
            pass
    try:
        message = resp.json().get("message", "")
        match = re.search(r"\[(\d+(?:\.\d+)?)\]", message)
        if match:
            return max(float(match.group(1)), 0.5)
    except Exception:
        pass
    return DEFAULT_RETRY_SECONDS


async def genesys_request(
    method: str,
    path: str,
    *,
    json: Optional[dict] = None,
    params: Optional[dict] = None,
) -> Any:
    token = await get_token()
    headers = h(token)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        for attempt in range(MAX_RETRIES + 1):
            resp = await client.request(
                method, f"{BASE_URL}{path}", json=json, params=params, headers=headers
            )
            if resp.status_code != 429 or attempt == MAX_RETRIES:
                break
            await asyncio.sleep(_retry_after_seconds(resp))

    if resp.status_code == 403:
        raise HTTPException(
            403,
            "Integração sem permissão de analytics (scope 'analytics:readonly' "
            "e/ou role com user detail). Adicione o scope ao OAuth Client e a "
            "permissão à role da integração nas divisões necessárias.",
        )
    if resp.status_code == 429:
        raise HTTPException(
            429,
            "Limite de taxa da Genesys esgotado após várias tentativas. "
            "Aguarde alguns segundos e tente novamente.",
        )
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, f"Genesys API: {resp.text[:300]}")
    return resp.json() if resp.text else {}


@router.get("/users/{user_id}/presence")
async def get_user_presence(
    user_id: str = Path(..., description="UUID Genesys do usuário"),
    date_str: str = Query(
        ...,
        alias="date",
        description="Dia civil YYYY-MM-DD (America/Sao_Paulo)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Presença (primaryPresence) do usuário no dia civil brasileiro.

    Intervalo calculado no backend com zoneinfo America/Sao_Paulo → UTC Z.
    """
    uid = user_id.strip("{}")
    if not UUID_REGEX.match(uid):
        raise HTTPException(422, "user_id deve ser um UUID válido.")

    try:
        day = date.fromisoformat(date_str)
    except ValueError as exc:
        raise HTTPException(422, f"Data inválida: {date_str}. Use YYYY-MM-DD.") from exc

    try:
        validate_presence_date(day)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    payload = {
        "interval": interval_for_br_date(day),
        "userFilters": [
            {
                "type": "or",
                "predicates": [{"dimension": "userId", "value": uid}],
            }
        ],
    }

    raw = await genesys_request(
        "POST",
        "/analytics/users/details/query",
        json=payload,
    )
    return build_presence_response(user_id=uid, day=day, payload=raw or {})
