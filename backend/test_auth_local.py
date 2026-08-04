"""
Testes do fluxo passwordless (magic link) e sliding session.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

import auth_local
import token_store
from config import settings
from main import app


@pytest.fixture
def auth_env(tmp_path, monkeypatch):
    """Usuários e tokens em arquivos temporários + JWT secreto de teste."""
    users_file = tmp_path / "users.json"
    tokens_file = tmp_path / "auth_tokens.json"

    users_file.write_text(
        json.dumps(
            {
                "users": [
                    {
                        "username": "alice",
                        "full_name": "Alice Teste",
                        "email": "alice@claro.com.br",
                        "hashed_password": "unused",
                        "role": "user",
                        "active": True,
                    },
                    {
                        "username": "admin",
                        "full_name": "Admin Teste",
                        "email": "admin@claro.com.br",
                        "hashed_password": "unused",
                        "role": "admin",
                        "active": True,
                    },
                    {
                        "username": "inactive",
                        "full_name": "Inativo",
                        "email": "inativo@claro.com.br",
                        "hashed_password": "unused",
                        "role": "user",
                        "active": False,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    tokens_file.write_text(json.dumps({"tokens": []}), encoding="utf-8")

    monkeypatch.setattr(auth_local, "USERS_FILE", str(users_file))
    monkeypatch.setattr(token_store, "TOKENS_FILE", str(tokens_file))
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "test-secret-key-for-auth-local")
    monkeypatch.setattr(settings, "JWT_EXPIRE_MINUTES", 2880)
    monkeypatch.setattr(settings, "MAGIC_LINK_EXPIRE_MINUTES", 10)
    monkeypatch.setattr(settings, "ALLOWED_EMAIL_DOMAIN", "claro.com.br")
    monkeypatch.setattr(settings, "APP_BASE_URL", "https://genesys.example.com")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test")

    return {"users_file": users_file, "tokens_file": tokens_file}


@pytest.mark.asyncio
async def test_login_rejects_wrong_domain(auth_env):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/auth/login", json={"email": "alguem@gmail.com"})
    assert response.status_code == 400
    assert "claro.com.br" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_unknown_email_returns_generic_200(auth_env):
    with patch("routes.auth_routes.send_magic_link") as mock_send:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/auth/login", json={"email": "naoexiste@claro.com.br"})
        mock_send.assert_not_called()

    assert response.status_code == 200
    assert "cadastrado" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_login_known_email_sends_magic_link(auth_env):
    with patch("routes.auth_routes.send_magic_link") as mock_send:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/auth/login", json={"email": "alice@claro.com.br"})
        mock_send.assert_called_once()
        assert mock_send.call_args.kwargs["to_email"] == "alice@claro.com.br"
        assert mock_send.call_args.kwargs["raw_token"]

    assert response.status_code == 200
    assert "cadastrado" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_login_send_failure_returns_actionable_502(auth_env):
    """Falha de envio (ex.: sandbox Resend) propaga detalhe no 502."""
    with patch(
        "routes.auth_routes.send_magic_link",
        side_effect=RuntimeError(
            "O Resend recusou o envio: com o remetente sandbox "
            "(onboarding@resend.dev) só é possível enviar para o e-mail da "
            "conta Resend. Verifique um domínio em https://resend.com/domains "
            "e configure RESEND_FROM_EMAIL com um endereço desse domínio."
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/auth/login", json={"email": "alice@claro.com.br"})

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "resend.com/domains" in detail.lower()
    assert "RESEND_FROM_EMAIL" in detail


def test_resend_failure_message_domain_restriction():
    from email_service import _resend_failure_message

    class _FakeResp:
        status_code = 403
        text = (
            '{"statusCode":403,"name":"validation_error","message":'
            '"You can only send testing emails to your own email address '
            '(owner@example.com). To send emails to other recipients, please '
            'verify a domain at resend.com/domains, and change the `from` '
            'address to an email using this domain."}'
        )

        def json(self):
            import json as _json

            return _json.loads(self.text)

    msg = _resend_failure_message(_FakeResp())
    assert "resend.com/domains" in msg
    assert "RESEND_FROM_EMAIL" in msg
    assert "onboarding@resend.dev" in msg


@pytest.mark.asyncio
async def test_verify_expired_token_fails(auth_env):
    raw = token_store.create_magic_link_token("alice", expire_minutes=10)
    # Força expiração no passado
    tokens = json.loads(auth_env["tokens_file"].read_text(encoding="utf-8"))["tokens"]
    tokens[0]["expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    auth_env["tokens_file"].write_text(json.dumps({"tokens": tokens}), encoding="utf-8")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/auth/verify?token={raw}", follow_redirects=False)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_verify_used_token_fails(auth_env):
    raw = token_store.create_magic_link_token("alice")
    assert token_store.consume_magic_link_token(raw) == "alice"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/auth/verify?token={raw}", follow_redirects=False)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_verify_sets_session_and_redirects(auth_env):
    raw = token_store.create_magic_link_token("alice")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/auth/verify?token={raw}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "https://genesys.example.com/"
    assert "access_token" in response.cookies

    cookie_token = response.cookies["access_token"]
    payload = jwt.decode(
        cookie_token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert payload["sub"] == "alice"


@pytest.mark.asyncio
async def test_sliding_session_renews_cookie(auth_env):
    token = auth_local.create_access_token(
        data={"sub": "alice"},
        expires_delta=timedelta(minutes=60),
    )
    old_payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/auth/me", cookies={"access_token": token})

    assert response.status_code == 200
    assert response.json()["username"] == "alice"
    assert "access_token" in response.cookies

    renewed = response.cookies["access_token"]
    assert renewed != token
    new_payload = jwt.decode(
        renewed,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert new_payload["sub"] == "alice"
    assert new_payload["exp"] > old_payload["exp"]


@pytest.mark.asyncio
async def test_idle_expired_session_returns_401(auth_env):
    expired = auth_local.create_access_token(
        data={"sub": "alice"},
        expires_delta=timedelta(seconds=-10),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/auth/me", cookies={"access_token": expired})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_session_cookie(auth_env):
    """Logout deve emitir Set-Cookie que remove access_token (max-age=0 / expires)."""
    token = auth_local.create_access_token(data={"sub": "alice"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/auth/logout", cookies={"access_token": token})

    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert "access_token=" in set_cookie
    assert "max-age=0" in set_cookie or "expires=" in set_cookie


def test_build_magic_link_uses_api_prefix(auth_env):
    from email_service import build_magic_link_url

    url = build_magic_link_url("abc123")
    assert url == "https://genesys.example.com/api/auth/verify?token=abc123"


@pytest.mark.parametrize(
    "to_email",
    [
        "athosroque@hotmail.com",
        "alguem@gmail.com",
        "user@outlook.com",
    ],
)
def test_send_magic_link_rejects_non_allowed_domain(auth_env, to_email):
    """Destinatários fora de ALLOWED_EMAIL_DOMAIN não chamam o Resend."""
    from email_service import send_magic_link

    with patch("email_service.httpx.post") as mock_post:
        with pytest.raises(RuntimeError, match="Envio recusado"):
            send_magic_link(to_email=to_email, raw_token="tok-test")
        mock_post.assert_not_called()


def test_send_magic_link_allows_claro_domain(auth_env):
    """@claro.com.br passa na validação e chega a chamar o Resend (mock)."""
    from email_service import send_magic_link

    with patch("email_service.httpx.post") as mock_post:
        mock_post.return_value.raise_for_status = lambda: None
        send_magic_link(to_email="alice@claro.com.br", raw_token="tok-ok")
        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        assert payload["to"] == ["alice@claro.com.br"]


def _admin_cookie() -> dict:
    token = auth_local.create_access_token(data={"sub": "admin"})
    return {"access_token": token}


@pytest.mark.asyncio
async def test_create_local_user_success(auth_env):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/auth/users",
            json={
                "email": "novo.usuario@claro.com.br",
                "full_name": "Novo Usuário",
                "role": "user",
            },
            cookies=_admin_cookie(),
        )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "novo.usuario@claro.com.br"
    assert body["full_name"] == "Novo Usuário"
    assert body["username"] == "novo.usuario"
    assert body["role"] == "user"
    assert body["active"] is True
    assert "hashed_password" not in body

    saved = json.loads(auth_env["users_file"].read_text(encoding="utf-8"))["users"]
    created = next(u for u in saved if u["username"] == "novo.usuario")
    assert created["hashed_password"]
    assert created["hashed_password"] != "unused"


@pytest.mark.asyncio
async def test_create_local_user_rejects_non_claro_email(auth_env):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/auth/users",
            json={
                "email": "alguem@gmail.com",
                "full_name": "Fora Domínio",
            },
            cookies=_admin_cookie(),
        )

    assert response.status_code == 400
    assert "claro.com.br" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_local_user_rejects_duplicate_email(auth_env):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/auth/users",
            json={
                "email": "alice@claro.com.br",
                "full_name": "Alice Duplicada",
            },
            cookies=_admin_cookie(),
        )

    assert response.status_code == 409
    assert "e-mail" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_local_user_success(auth_env):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete("/auth/users/alice", cookies=_admin_cookie())

    assert response.status_code == 200
    assert response.json()["username"] == "alice"

    saved = json.loads(auth_env["users_file"].read_text(encoding="utf-8"))["users"]
    assert not any(u["username"] == "alice" for u in saved)


@pytest.mark.asyncio
async def test_delete_local_user_rejects_self(auth_env):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete("/auth/users/admin", cookies=_admin_cookie())

    assert response.status_code == 400
    assert "próprio" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_local_user_other_admin_ok(auth_env):
    """Com dois admins, excluir o outro admin é permitido."""
    users = json.loads(auth_env["users_file"].read_text(encoding="utf-8"))["users"]
    users.append(
        {
            "username": "admin2",
            "full_name": "Admin Dois",
            "email": "admin2@claro.com.br",
            "hashed_password": "unused",
            "role": "admin",
            "active": True,
        }
    )
    auth_env["users_file"].write_text(json.dumps({"users": users}), encoding="utf-8")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete("/auth/users/admin2", cookies=_admin_cookie())

    assert response.status_code == 200
    saved = json.loads(auth_env["users_file"].read_text(encoding="utf-8"))["users"]
    assert not any(u["username"] == "admin2" for u in saved)
    assert any(u["username"] == "admin" and u["role"] == "admin" for u in saved)


@pytest.mark.asyncio
async def test_delete_local_user_rejects_last_admin(auth_env):
    """Defense-in-depth: último admin não pode ser removido (caller ≠ alvo via override)."""
    auth_env["users_file"].write_text(
        json.dumps(
            {
                "users": [
                    {
                        "username": "onlyadmin",
                        "full_name": "Único Admin",
                        "email": "onlyadmin@claro.com.br",
                        "hashed_password": "unused",
                        "role": "admin",
                        "active": True,
                    },
                    {
                        "username": "bob",
                        "full_name": "Bob",
                        "email": "bob@claro.com.br",
                        "hashed_password": "unused",
                        "role": "user",
                        "active": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    async def _fake_admin():
        return {
            "username": "operator",
            "full_name": "Operator",
            "email": "operator@claro.com.br",
            "role": "admin",
            "active": True,
        }

    app.dependency_overrides[auth_local.require_admin] = _fake_admin
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.delete("/auth/users/onlyadmin")
    finally:
        app.dependency_overrides.pop(auth_local.require_admin, None)

    assert response.status_code == 400
    assert "último administrador" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_local_user_not_found(auth_env):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete("/auth/users/naoexiste", cookies=_admin_cookie())

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_local_user_requires_admin(auth_env):
    token = auth_local.create_access_token(data={"sub": "alice"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete(
            "/auth/users/inactive",
            cookies={"access_token": token},
        )

    assert response.status_code == 403
