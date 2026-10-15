"""
Serviço TOTP (Time-based One-Time Password) para autenticação de dois fatores.

Responsabilidades:
- Gerar segredos TOTP e URIs de provisionamento (QR)
- Criptografar segredos em repouso com Fernet
- Validar códigos com replay protection (totp_last_step)
- Gerar e consumir códigos de recuperação (uso único)
"""
from __future__ import annotations

import secrets
import hashlib
from typing import Optional, Tuple

import pyotp
from cryptography.fernet import Fernet, InvalidToken

from config import settings


def generate_secret() -> str:
    """
    Gera um segredo TOTP aleatório em base32.

    Retorna:
        str: Segredo base32 aleatorio pronto para provisionar em autenticador.
    """
    return pyotp.random_base32()


def provisioning_uri(username: str, secret: str) -> str:
    """
    Gera a URI otpauth:// para provisionamento em aplicativos autenticadores.

    Argumentos:
        username: Nome de usuário ou e-mail para exibição no autenticador.
        secret: Segredo base32 gerado por generate_secret().

    Retorna:
        str: URI otpauth:// (pronta para gerar QR code ou input manual).
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=username,
        issuer_name="Genesys Manager",
    )


def encrypt_secret(secret: str) -> str:
    """
    Criptografa um segredo TOTP com Fernet.

    Argumentos:
        secret: Segredo em texto plano a criptografar.

    Retorna:
        str: Segredo criptografado (token Fernet base64).

    Levanta:
        RuntimeError: Se TOTP_ENCRYPTION_KEY não está configurada.
    """
    if not settings.TOTP_ENCRYPTION_KEY:
        raise RuntimeError(
            "TOTP_ENCRYPTION_KEY não configurada. "
            "Defina a variável de ambiente ou validate_production_settings falhará."
        )

    cipher = Fernet(settings.TOTP_ENCRYPTION_KEY.encode())
    encrypted = cipher.encrypt(secret.encode())
    return encrypted.decode()


def decrypt_secret(encrypted_token: str) -> str:
    """
    Descriptografa um segredo TOTP com Fernet.

    Argumentos:
        encrypted_token: Token criptografado de encrypt_secret().

    Retorna:
        str: Segredo em texto plano.

    Levanta:
        RuntimeError: Se a chave não está configurada ou token é inválido.
    """
    if not settings.TOTP_ENCRYPTION_KEY:
        raise RuntimeError(
            "TOTP_ENCRYPTION_KEY não configurada. "
            "Defina a variável de ambiente ou validate_production_settings falhará."
        )

    try:
        cipher = Fernet(settings.TOTP_ENCRYPTION_KEY.encode())
        decrypted = cipher.decrypt(encrypted_token.encode())
        return decrypted.decode()
    except (InvalidToken, ValueError) as e:
        raise RuntimeError(f"Falha ao descriptografar segredo TOTP: {e}")


def verify_code(
    user: dict,
    code: str,
    secret_field: str = "totp_secret_enc",
) -> bool:
    """
    Valida um código TOTP de 6 dígitos com proteção contra replay.

    Estratégia de validação:
    - Aceita valid_window=1 (30s atual + 30s anterior/próximo para relógio dessincronizado).
    - Extrai o timestamp step do código validado (0 se não valida).
    - Rejeita se step <= último step usufruído (totp_last_step).
    - Persiste o novo step em users.json e atualiza user dict.
    - Retorna False silenciosamente em erros (input ruins, segredo inválido, etc.).

    Argumentos:
        user: Dicionário do usuário contendo totp_secret_enc (criptografado).
        code: Código de 6 dígitos (aceita espaços que serão removidos).
        secret_field: Campo no user dict onde buscar o segredo criptografado.

    Retorna:
        bool: True se código válido e não é replay; False caso contrário.
    """
    try:
        # Localizar segredo criptografado no usuário
        encrypted_secret = user.get(secret_field)
        if not encrypted_secret:
            return False

        # Descriptografar
        try:
            secret = decrypt_secret(encrypted_secret)
        except RuntimeError:
            return False

        # Limpar espaços do código
        code_clean = code.strip()

        # Validar formato (6 dígitos)
        if not code_clean.isdigit() or len(code_clean) != 6:
            return False

        # Criar verificador TOTP
        totp = pyotp.TOTP(secret)

        # Validar código com janela para relógio dessincronizado
        # valid_window=1 significa: -30s (step anterior), 0 (agora), +30s (step próximo)
        time_step = None
        for step_offset in [-1, 0, 1]:
            if totp.verify(code_clean, valid_window=0):
                # Computar o step exato para este offset
                import time
                current_time = int(time.time())
                time_step = (current_time // 30) + step_offset
                break

        # Se nenhum offset validou, tenta com valid_window=1 direto
        if time_step is None:
            # Último recurso: usa valid_window=1 e computa step aproximado
            if not totp.verify(code_clean, valid_window=1):
                return False
            # Calcula o step mais provável (atual)
            import time
            time_step = int(time.time()) // 30

        # Proteção contra replay
        last_step = user.get("totp_last_step", -1)
        if isinstance(last_step, int) and time_step <= last_step:
            return False

        # Buscar e salvar último step usado em users.json
        try:
            # Evitar circular imports: import lazily
            import auth_local

            users = auth_local.load_users()
            username = user.get("username")
            if not username:
                return False

            # Localizar o usuário no arquivo
            user_entry = next((u for u in users if u["username"] == username), None)
            if not user_entry:
                return False

            # Atualizar último step
            user_entry["totp_last_step"] = time_step
            auth_local.save_users(users)

            # Atualizar também a cópia local (dict passado)
            user["totp_last_step"] = time_step

            return True
        except Exception:
            # Se falha em salvar (ex.: arquivo indisponível), rejeita o código
            return False

    except Exception:
        # Qualquer outro erro: falha silenciosa
        return False


def generate_recovery_codes(n: int = 10) -> Tuple[list[str], list[str]]:
    """
    Gera códigos de recuperação (backup codes) no formato 'ABCDE-12345'.

    Retorna dois lists: códigos em texto plano e seus hashes SHA-256.
    Os códigos planos devem ser exibidos uma única vez ao usuário.
    Os hashes são armazenados em users.json para validação única.

    Argumentos:
        n: Número de códigos a gerar (padrão 10).

    Retorna:
        Tupla (plain_codes, hashed_codes):
        - plain_codes: list[str] com códigos legíveis (ex: 'ABCDE-12345').
        - hashed_codes: list[str] com hashes SHA-256 dos plain_codes.
    """
    plain_codes = []
    hashed_codes = []

    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    for _ in range(n):
        # Formato: 5 letras - 5 dígitos
        part1 = "".join(secrets.choice(alphabet) for _ in range(5))
        part2 = "".join(secrets.choice("0123456789") for _ in range(5))
        code = f"{part1}-{part2}"

        plain_codes.append(code)

        # Hash SHA-256 para armazenar
        try:
            # Lazy import para evitar circular dependency
            import token_store
            code_hash = token_store.hash_token(code)
        except ImportError:
            # Fallback manual se token_store não estiver disponível
            code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()

        hashed_codes.append(code_hash)

    return plain_codes, hashed_codes


def consume_recovery_code(username: str, code: str) -> bool:
    """
    Consome um código de recuperação (uso único).

    Localiza o hash do código em users.json[username].totp_recovery_hashes,
    remove-o (uso único) e salva de volta.

    Argumentos:
        username: Nome de usuário.
        code: Código de recuperação em texto plano (será normalizado e hasheado).

    Retorna:
        bool: True se código encontrado e consumido; False se não encontrado ou erro.
    """
    try:
        # Normalizar: strip e maiúsculas
        code_clean = code.strip().upper()

        # Lazy import para evitar circular dependency
        import auth_local
        import token_store

        # Carregar usuários
        users = auth_local.load_users()
        user = next((u for u in users if u["username"] == username), None)
        if not user:
            return False

        # Obter hashes armazenados
        recovery_hashes = user.get("totp_recovery_hashes", [])
        if not recovery_hashes:
            return False

        # Computar hash do código fornecido
        code_hash = token_store.hash_token(code_clean)

        # Procurar e remover
        if code_hash not in recovery_hashes:
            return False

        # Remover (uso único)
        recovery_hashes.remove(code_hash)
        user["totp_recovery_hashes"] = recovery_hashes

        # Salvar de volta
        auth_local.save_users(users)

        return True
    except Exception:
        # Qualquer erro: rejeita o código
        return False
