"""
Testes para os endpoints 2FA (TOTP) — setup, confirm, verify, e reset.

Cobertura:
- POST /verify retorna pré-autenticação (ambos status)
- pre_auth cookie em /me retorna 401
- Flow setup+confirm com código gerado por pyotp
- Código inválido 401
- Replay rejeitado
- 6ª tentativa 429 (rate limit)
- Código de recuperação uso único
- Token sem mfa em /me retorna 401
- Reset admin
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import pyotp
from httpx import ASGITransport, AsyncClient
from jose import jwt

import auth_local
import token_store
import totp_service
from rate_limit import reset_rate_limits
from config import settings
from main import app


@pytest.fixture
def auth_env_2fa(tmp_path, monkeypatch):
    """Fixture com usuários para testes de 2FA."""
    users_file = tmp_path / "users.json"
    tokens_file = tmp_path / "auth_tokens.json"

    # Usuários de teste
    users_data = {
        "users": [
            {
                "username": "alice",
                "full_name": "Alice Test",
                "email": "alice@claro.com.br",
                "hashed_password": "unused",
                "role": "user",
                "active": True,
                # sem totp_* (primeiro login)
            },
            {
                "username": "bob",
                "full_name": "Bob Test",
                "email": "bob@claro.com.br",
                "hashed_password": "unused",
                "role": "user",
                "active": True,
                "totp_enabled": True,
                # totp_secret_enc será preenchido nos testes
            },
            {
                "username": "admin",
                "full_name": "Admin Test",
                "email": "admin@claro.com.br",
                "hashed_password": "unused",
                "role": "admin",
                "active": True,
            },
        ]
    }

    users_file.write_text(json.dumps(users_data), encoding="utf-8")
    tokens_file.write_text(json.dumps({"tokens": []}), encoding="utf-8")

    monkeypatch.setattr(auth_local, "USERS_FILE", str(users_file))
    monkeypatch.setattr(token_store, "TOKENS_FILE", str(tokens_file))
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "test-secret-key-2fa")
    monkeypatch.setattr(settings, "JWT_EXPIRE_MINUTES", 2880)
    monkeypatch.setattr(settings, "MAGIC_LINK_EXPIRE_MINUTES", 10)
    monkeypatch.setattr(settings, "ALLOWED_EMAIL_DOMAIN", "claro.com.br")
    monkeypatch.setattr(settings, "APP_BASE_URL", "https://genesys.example.com")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test")

    # TOTP encryption key (Fernet)
    from cryptography.fernet import Fernet
    encryption_key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "TOTP_ENCRYPTION_KEY", encryption_key)

    reset_rate_limits()

    return {"users_file": users_file, "tokens_file": tokens_file}


@pytest.mark.asyncio
async def test_verify_returns_preauth_setup_required(auth_env_2fa):
    """POST /verify com magic link válido retorna pré-auth + status='totp_setup_required'."""
    # Criar magic link válido para alice (sem 2FA)
    username = "alice"
    raw_token = token_store.create_magic_link_token(username, purpose="login")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/auth/verify", json={"token": raw_token})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "totp_setup_required"

    # Verificar cookie pré-autenticação
    cookies = response.cookies
    assert "pre_auth_token" in cookies


@pytest.mark.asyncio
async def test_verify_returns_preauth_totp_required(auth_env_2fa):
    """POST /verify com magic link válido retorna pré-auth + status='totp_required' (2FA já ativado)."""
    # Preparar bob (2FA já ativado)
    username = "bob"
    secret = totp_service.generate_secret()
    encrypted = totp_service.encrypt_secret(secret)

    users = auth_local.load_users()
    user = next(u for u in users if u["username"] == username)
    user["totp_secret_enc"] = encrypted
    auth_local.save_users(users)

    raw_token = token_store.create_magic_link_token(username, purpose="login")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/auth/verify", json={"token": raw_token})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "totp_required"

    cookies = response.cookies
    assert "pre_auth_token" in cookies


@pytest.mark.asyncio
async def test_preauth_cookie_on_me_returns_401(auth_env_2fa):
    """GET /me com apenas pré-auth cookie (sem access_token) retorna 401."""
    # Criar pré-auth token
    pre_auth = auth_local.create_pre_auth_token("alice")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("pre_auth_token", pre_auth)
        response = await ac.get("/auth/me")

    assert response.status_code == 401
    assert "pré-autenticação" in response.json()["detail"].lower() or \
           "login" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_setup_confirm_flow_alice(auth_env_2fa):
    """Flow completo: magic link -> setup -> confirm com código gerado -> sessão ativa."""
    username = "alice"

    # 1. Obter pré-auth
    raw_magic = token_store.create_magic_link_token(username, purpose="login")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/auth/verify", json={"token": raw_magic})
    assert r.status_code == 200
    pre_auth_cookie = r.cookies.get("pre_auth_token")

    # 2. Setup
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("pre_auth_token", pre_auth_cookie)
        r = await ac.post("/auth/2fa/setup")
    assert r.status_code == 200
    data = r.json()
    assert "otpauth_uri" in data
    assert "secret" in data
    secret = data["secret"]

    # 3. Gerar código com pyotp
    totp = pyotp.TOTP(secret)
    code = totp.now()

    # 4. Confirm
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("pre_auth_token", pre_auth_cookie)
        r = await ac.post("/auth/2fa/confirm-setup", json={"code": code})
    assert r.status_code == 200
    data = r.json()
    assert "recovery_codes" in data
    assert len(data["recovery_codes"]) == 10
    assert "user" in data

    # Verificar session cookie
    access_token = r.cookies.get("access_token")
    assert access_token is not None

    # 5. Confirmar que /me agora funciona
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", access_token)
        r = await ac.get("/auth/me")
    assert r.status_code == 200
    user = r.json()
    assert user["username"] == username
    assert user.get("totp_enabled") is True

    # 6. Regressão: o código usado no setup não pode ser reutilizado (anti-replay)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("pre_auth_token", pre_auth_cookie)
        r = await ac.post("/auth/2fa/verify", json={"code": code})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_confirm_wrong_code_returns_401(auth_env_2fa):
    """POST /2fa/confirm-setup com código inválido retorna 401."""
    username = "alice"

    # Setup flow
    raw_magic = token_store.create_magic_link_token(username, purpose="login")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/auth/verify", json={"token": raw_magic})
    pre_auth_cookie = r.cookies.get("pre_auth_token")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("pre_auth_token", pre_auth_cookie)
        r = await ac.post("/auth/2fa/setup")
    assert r.status_code == 200

    # Tentar confirm com código errado
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("pre_auth_token", pre_auth_cookie)
        r = await ac.post("/auth/2fa/confirm-setup", json={"code": "000000"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_replay_attack_rejected(auth_env_2fa):
    """POST /2fa/verify com mesmo código (replay) retorna 401."""
    username = "bob"

    # Preparar bob com 2FA
    secret = totp_service.generate_secret()
    encrypted = totp_service.encrypt_secret(secret)
    users = auth_local.load_users()
    user = next(u for u in users if u["username"] == username)
    user["totp_secret_enc"] = encrypted
    user["totp_last_step"] = -1  # Nunca usou
    auth_local.save_users(users)

    # Gerar código válido
    totp = pyotp.TOTP(secret)
    code = totp.now()

    # 1º uso: deve funcionar
    pre_auth = auth_local.create_pre_auth_token(username)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("pre_auth_token", pre_auth)
        r = await ac.post("/auth/2fa/verify", json={"code": code})
    assert r.status_code == 200

    # 2º uso (replay): deve falhar
    pre_auth2 = auth_local.create_pre_auth_token(username)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("pre_auth_token", pre_auth2)
        r = await ac.post("/auth/2fa/verify", json={"code": code})
    assert r.status_code == 401
    assert "inválido" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_rate_limit_6th_attempt_429(auth_env_2fa):
    """6ª tentativa em 15 min retorna 429."""
    username = "bob"

    # Preparar bob
    secret = totp_service.generate_secret()
    encrypted = totp_service.encrypt_secret(secret)
    users = auth_local.load_users()
    user = next(u for u in users if u["username"] == username)
    user["totp_secret_enc"] = encrypted
    auth_local.save_users(users)

    # 5 tentativas com código errado
    for i in range(5):
        pre_auth = auth_local.create_pre_auth_token(username)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            ac.cookies.set("pre_auth_token", pre_auth)
            r = await ac.post("/auth/2fa/verify", json={"code": "000000"})
        assert r.status_code == 401

    # 6ª tentativa: rate limit
    pre_auth = auth_local.create_pre_auth_token(username)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("pre_auth_token", pre_auth)
        r = await ac.post("/auth/2fa/verify", json={"code": "000000"})
    assert r.status_code == 429


@pytest.mark.asyncio
async def test_recovery_code_single_use(auth_env_2fa):
    """Código de recuperação pode ser usado apenas uma vez."""
    username = "alice"

    # Setup + confirm para gerar recovery codes
    raw_magic = token_store.create_magic_link_token(username, purpose="login")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/auth/verify", json={"token": raw_magic})
    pre_auth_cookie = r.cookies.get("pre_auth_token")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("pre_auth_token", pre_auth_cookie)
        r = await ac.post("/auth/2fa/setup")
    secret = r.json()["secret"]

    totp = pyotp.TOTP(secret)
    code = totp.now()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("pre_auth_token", pre_auth_cookie)
        r = await ac.post("/auth/2fa/confirm-setup", json={"code": code})
    recovery_codes = r.json()["recovery_codes"]
    recovery_code = recovery_codes[0]

    # Novo magic link para tentar usar recovery code
    raw_magic2 = token_store.create_magic_link_token(username, purpose="login")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/auth/verify", json={"token": raw_magic2})
    pre_auth_cookie2 = r.cookies.get("pre_auth_token")

    # 1º uso: válido
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("pre_auth_token", pre_auth_cookie2)
        r = await ac.post("/auth/2fa/verify", json={"recovery_code": recovery_code})
    assert r.status_code == 200

    # 2º uso: invalido (já consumido)
    raw_magic3 = token_store.create_magic_link_token(username, purpose="login")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/auth/verify", json={"token": raw_magic3})
    pre_auth_cookie3 = r.cookies.get("pre_auth_token")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("pre_auth_token", pre_auth_cookie3)
        r = await ac.post("/auth/2fa/verify", json={"recovery_code": recovery_code})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_token_without_mfa_on_me_returns_401(auth_env_2fa):
    """Token sem mfa=true em /me retorna 401."""
    # Criar token manualmente sem mfa (ou com mfa=false)
    token_data = {"sub": "alice", "mfa": False}
    token = auth_local.create_access_token(token_data)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        r = await ac.get("/auth/me")

    assert r.status_code == 401
    assert "múltiplos fatores" in r.json()["detail"].lower() or \
           "mfa" in r.json()["detail"].lower() or \
           "login" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_reset_2fa_success(auth_env_2fa):
    """Admin pode resetar 2FA de outro usuário."""
    target_username = "bob"
    admin_username = "admin"

    # Preparar bob com 2FA
    secret = totp_service.generate_secret()
    encrypted = totp_service.encrypt_secret(secret)
    users = auth_local.load_users()
    bob = next(u for u in users if u["username"] == target_username)
    bob["totp_secret_enc"] = encrypted
    bob["totp_enabled"] = True
    bob["totp_recovery_hashes"] = ["hash1", "hash2"]
    auth_local.save_users(users)

    # Admin login
    raw_magic = token_store.create_magic_link_token(admin_username, purpose="login")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/auth/verify", json={"token": raw_magic})

    # Admin precisa de sessão (sem 2FA no teste)
    access_token = auth_local.create_access_token({"sub": admin_username, "mfa": True})

    # Admin reseta bob's 2FA
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", access_token)
        r = await ac.post(f"/auth/users/{target_username}/2fa/reset")

    assert r.status_code == 200
    assert target_username in r.json()["message"]

    # Verificar que campos foram removidos
    users = auth_local.load_users()
    bob = next(u for u in users if u["username"] == target_username)
    assert "totp_secret_enc" not in bob
    assert "totp_enabled" not in bob
    assert "totp_recovery_hashes" not in bob


@pytest.mark.asyncio
async def test_admin_cannot_reset_own_2fa(auth_env_2fa):
    """Admin não pode resetar sua própria 2FA."""
    admin_username = "admin"

    # Admin login
    access_token = auth_local.create_access_token({"sub": admin_username, "mfa": True})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", access_token)
        r = await ac.post(f"/auth/users/{admin_username}/2fa/reset")

    assert r.status_code == 400
    detail_lower = r.json()["detail"].lower()
    assert "própria" in detail_lower or "próprio" in detail_lower


@pytest.mark.asyncio
async def test_admin_reset_nonexistent_user_returns_404(auth_env_2fa):
    """Reset 2FA de usuário inexistente retorna 404."""
    admin_username = "admin"

    access_token = auth_local.create_access_token({"sub": admin_username, "mfa": True})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", access_token)
        r = await ac.post("/auth/users/nonexistent/2fa/reset")

    assert r.status_code == 404
