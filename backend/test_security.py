"""
Guardas de segurança: toda rota de negócio exige sessão e o login tem rate limit.
"""
from __future__ import annotations

import pytest
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

from auth_local import get_current_user, require_admin
from main import app
from rate_limit import reset_rate_limits

# Rotas que precisam ser públicas para o fluxo de login funcionar
ROTAS_PUBLICAS = {
    "/auth/login",
    "/auth/verify",
    "/auth/logout",
    "/health",
}


def _deps_da_rota(route: APIRoute) -> set:
    """Coleta recursivamente as funções de dependência da rota."""
    encontradas = set()
    pilha = [route.dependant]
    while pilha:
        dep = pilha.pop()
        if dep.call is not None:
            encontradas.add(dep.call)
        pilha.extend(dep.dependencies)
    return encontradas


def test_todas_as_rotas_exigem_autenticacao():
    abertas = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or route.path in ROTAS_PUBLICAS:
            continue
        if not _deps_da_rota(route) & {get_current_user, require_admin}:
            abertas.append(f"{sorted(route.methods)} {route.path}")
    assert not abertas, f"Rotas sem autenticação: {abertas}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/tickets/"),
        ("PUT", "/tickets/abc"),
        ("POST", "/tickets/sync"),
        ("GET", "/system-diagnostics/flow?name_or_id=x"),
        ("GET", "/auth/test"),
        ("GET", "/config/groups"),
    ],
)
async def test_rotas_antes_abertas_retornam_401_sem_cookie(method, path):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.request(method, path, json={"classification": "x", "is_faq": False})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_tem_rate_limit_por_email():
    reset_rate_limits()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        codes = [
            (await ac.post("/auth/login", json={"email": "spam@gmail.com"})).status_code
            for _ in range(6)
        ]
    reset_rate_limits()
    assert codes[:5] == [400] * 5
    assert codes[5] == 429
