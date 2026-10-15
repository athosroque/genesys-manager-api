"""
Testes unitários do serviço TOTP (Two-Factor Authentication).

Cobertura:
- Geração de segredo e URI de provisionamento
- Criptografia e descriptografia de segredos
- Validação de códigos com anti-replay
- Geração e consumo único de códigos de recuperação
"""
from __future__ import annotations

import json
import pytest
import pyotp
from cryptography.fernet import Fernet

import auth_local
import token_store
import totp_service
from config import settings


@pytest.fixture
def totp_env(tmp_path, monkeypatch):
    """
    Configura ambiente TOTP de teste.

    - USERS_FILE em arquivo temporário
    - TOTP_ENCRYPTION_KEY com chave Fernet válida
    - JWT_SECRET_KEY de teste
    """
    users_file = tmp_path / "users.json"
    totp_key = Fernet.generate_key().decode()

    # Usuários iniciais
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
                        "username": "bob",
                        "full_name": "Bob Teste",
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

    # Monkey patch
    monkeypatch.setattr(auth_local, "USERS_FILE", str(users_file))
    monkeypatch.setattr(settings, "TOTP_ENCRYPTION_KEY", totp_key)
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "test-secret-key-totp")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")

    return {
        "users_file": users_file,
        "totp_key": totp_key,
    }


def test_generate_secret(totp_env):
    """Gera segredo TOTP válido em base32."""
    secret = totp_service.generate_secret()
    assert isinstance(secret, str)
    assert len(secret) > 0
    # Base32 contém apenas A-Z e 2-7
    assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in secret)
    # Dois secrets devem ser diferentes
    secret2 = totp_service.generate_secret()
    assert secret != secret2


def test_provisioning_uri(totp_env):
    """Gera URI otpauth:// para provisionamento (QR code)."""
    secret = totp_service.generate_secret()
    uri = totp_service.provisioning_uri("alice@claro.com.br", secret)
    assert uri.startswith("otpauth://totp/")
    assert "alice%40claro.com.br" in uri or "alice@claro.com.br" in uri
    assert "Genesys%20Manager" in uri  # issuer_name codificado em URL
    assert secret in uri


def test_encrypt_decrypt_roundtrip(totp_env):
    """Criptografa e descriptografa segredo mantendo o valor."""
    original_secret = totp_service.generate_secret()

    encrypted = totp_service.encrypt_secret(original_secret)
    assert encrypted != original_secret
    assert isinstance(encrypted, str)

    decrypted = totp_service.decrypt_secret(encrypted)
    assert decrypted == original_secret


def test_encrypt_with_missing_key(totp_env, monkeypatch):
    """Criptografia falha se TOTP_ENCRYPTION_KEY vazio."""
    monkeypatch.setattr(settings, "TOTP_ENCRYPTION_KEY", "")

    with pytest.raises(RuntimeError, match="TOTP_ENCRYPTION_KEY"):
        totp_service.encrypt_secret("some-secret")


def test_decrypt_with_missing_key(totp_env, monkeypatch):
    """Descriptografia falha se TOTP_ENCRYPTION_KEY vazio."""
    monkeypatch.setattr(settings, "TOTP_ENCRYPTION_KEY", "")

    with pytest.raises(RuntimeError, match="TOTP_ENCRYPTION_KEY"):
        totp_service.decrypt_secret("encrypted-token")


def test_decrypt_with_invalid_token(totp_env):
    """Descriptografia falha com token corrompido."""
    with pytest.raises(RuntimeError, match="Falha ao descriptografar"):
        totp_service.decrypt_secret("invalid-fernet-token")


def test_verify_code_valid(totp_env):
    """Código TOTP válido é aceito."""
    # Gerar segredo e criptografar
    secret = totp_service.generate_secret()
    encrypted = totp_service.encrypt_secret(secret)

    # Criar usuário com segredo criptografado
    user = {
        "username": "alice",
        "totp_secret_enc": encrypted,
        "totp_last_step": -1,
    }

    # Gerar código válido
    totp = pyotp.TOTP(secret)
    code = totp.now()

    # Verificar
    result = totp_service.verify_code(user, code)
    assert result is True
    assert user.get("totp_last_step") is not None and user.get("totp_last_step") >= 0

    # Persistência: verificar que foi salvo em users.json
    users = auth_local.load_users()
    alice = next(u for u in users if u["username"] == "alice")
    assert alice.get("totp_last_step") == user.get("totp_last_step")


def test_verify_code_strips_spaces(totp_env):
    """Código com espaços é aceito após limpeza."""
    secret = totp_service.generate_secret()
    encrypted = totp_service.encrypt_secret(secret)

    user = {
        "username": "alice",
        "totp_secret_enc": encrypted,
        "totp_last_step": -1,
    }

    totp = pyotp.TOTP(secret)
    code = totp.now()
    code_with_spaces = f"  {code}  "  # Espaços ao redor

    result = totp_service.verify_code(user, code_with_spaces)
    assert result is True


def test_verify_code_rejects_wrong_format(totp_env):
    """Código com formato inválido é rejeitado."""
    secret = totp_service.generate_secret()
    encrypted = totp_service.encrypt_secret(secret)

    user = {
        "username": "alice",
        "totp_secret_enc": encrypted,
    }

    # Não é número
    assert totp_service.verify_code(user, "abcdef") is False

    # Número mas não 6 dígitos
    assert totp_service.verify_code(user, "12345") is False
    assert totp_service.verify_code(user, "1234567") is False


def test_verify_code_rejects_replay(totp_env):
    """Mesmo código não é aceito duas vezes (replay protection)."""
    secret = totp_service.generate_secret()
    encrypted = totp_service.encrypt_secret(secret)

    user = {
        "username": "alice",
        "totp_secret_enc": encrypted,
        "totp_last_step": -1,
    }

    totp = pyotp.TOTP(secret)
    code = totp.now()

    # Primeiro uso: aceito
    result1 = totp_service.verify_code(user, code)
    assert result1 is True

    # Segundo uso: rejeitado (mesmo step)
    result2 = totp_service.verify_code(user, code)
    assert result2 is False


def test_verify_code_missing_secret(totp_env):
    """Código é rejeitado se usuário não tem segredo."""
    user = {
        "username": "alice",
        # totp_secret_enc ausente
    }

    result = totp_service.verify_code(user, "123456")
    assert result is False


def test_verify_code_invalid_encrypted_secret(totp_env):
    """Código é rejeitado se segredo criptografado é inválido."""
    user = {
        "username": "alice",
        "totp_secret_enc": "invalid-fernet-token",
    }

    result = totp_service.verify_code(user, "123456")
    assert result is False


def test_verify_code_user_not_in_file(totp_env):
    """Código é rejeitado se usuário não existe em users.json."""
    secret = totp_service.generate_secret()
    encrypted = totp_service.encrypt_secret(secret)

    # Usuário que não existe no arquivo
    user = {
        "username": "naoexiste",
        "totp_secret_enc": encrypted,
    }

    totp = pyotp.TOTP(secret)
    code = totp.now()

    result = totp_service.verify_code(user, code)
    assert result is False


def test_generate_recovery_codes(totp_env):
    """Gera códigos de recuperação em formato válido."""
    plain, hashed = totp_service.generate_recovery_codes(n=10)

    assert len(plain) == 10
    assert len(hashed) == 10

    # Verificar formato dos códigos planos: ABCDE-12345
    for code in plain:
        parts = code.split("-")
        assert len(parts) == 2
        assert len(parts[0]) == 5
        assert len(parts[1]) == 5
        assert parts[0].isalnum()
        assert parts[1].isalnum()

    # Hashes são hex strings (SHA-256)
    for code_hash in hashed:
        assert len(code_hash) == 64  # SHA-256 = 64 caracteres hex
        assert all(c in "0123456789abcdef" for c in code_hash)

    # Todos os códigos são únicos
    assert len(set(plain)) == 10
    assert len(set(hashed)) == 10


def test_generate_recovery_codes_custom_count(totp_env):
    """Gera número customizado de códigos."""
    plain, hashed = totp_service.generate_recovery_codes(n=5)
    assert len(plain) == 5
    assert len(hashed) == 5


def test_consume_recovery_code_success(totp_env):
    """Consome código de recuperação (uso único)."""
    # Gerar códigos
    plain, hashed = totp_service.generate_recovery_codes(n=2)

    # Atualizar usuário com hashes
    users = auth_local.load_users()
    alice = next(u for u in users if u["username"] == "alice")
    alice["totp_recovery_hashes"] = hashed
    auth_local.save_users(users)

    # Consumir primeiro código
    result = totp_service.consume_recovery_code("alice", plain[0])
    assert result is True

    # Verificar que foi removido
    users = auth_local.load_users()
    alice = next(u for u in users if u["username"] == "alice")
    assert len(alice["totp_recovery_hashes"]) == 1

    # Tentar consumir novamente: falha (uso único)
    result = totp_service.consume_recovery_code("alice", plain[0])
    assert result is False

    # Segundo código ainda funciona
    result = totp_service.consume_recovery_code("alice", plain[1])
    assert result is True


def test_consume_recovery_code_normalizes_input(totp_env):
    """Código com espaços e minúsculas é normalizado."""
    plain, hashed = totp_service.generate_recovery_codes(n=1)

    users = auth_local.load_users()
    alice = next(u for u in users if u["username"] == "alice")
    alice["totp_recovery_hashes"] = hashed
    auth_local.save_users(users)

    # Fornecer com espaços e minúsculas
    messy_code = f"  {plain[0].lower()}  "
    result = totp_service.consume_recovery_code("alice", messy_code)
    assert result is True


def test_consume_recovery_code_invalid_code(totp_env):
    """Código inválido é rejeitado."""
    users = auth_local.load_users()
    alice = next(u for u in users if u["username"] == "alice")
    alice["totp_recovery_hashes"] = ["abc123def456..."]  # Algum hash
    auth_local.save_users(users)

    result = totp_service.consume_recovery_code("alice", "INVALID-12345")
    assert result is False


def test_consume_recovery_code_user_not_found(totp_env):
    """Código é rejeitado se usuário não existe."""
    result = totp_service.consume_recovery_code("naoexiste", "ABCDE-12345")
    assert result is False


def test_consume_recovery_code_empty_hashes(totp_env):
    """Código é rejeitado se usuário não tem recovery codes."""
    users = auth_local.load_users()
    alice = next(u for u in users if u["username"] == "alice")
    # Sem totp_recovery_hashes ou vazio
    alice.pop("totp_recovery_hashes", None)
    auth_local.save_users(users)

    result = totp_service.consume_recovery_code("alice", "ABCDE-12345")
    assert result is False
