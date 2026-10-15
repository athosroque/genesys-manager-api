from typing import Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from auth_local import (
    create_access_token,
    get_current_user,
    require_admin,
    get_pre_auth_user,
    load_users,
    save_users,
    hash_password,
    generate_password,
    find_user_by_email,
    is_allowed_email_domain,
    set_session_cookie,
    clear_session_cookie,
    set_pre_auth_cookie,
    clear_pre_auth_cookie,
    create_pre_auth_token,
    sanitize_user,
)
from config import settings
from email_service import send_magic_link
from rate_limit import check_rate_limit
from token_store import (
    create_magic_link_token,
    consume_magic_link_token,
    peek_magic_link_token,
)
from totp_service import (
    generate_secret,
    provisioning_uri,
    encrypt_secret,
    decrypt_secret,
    verify_code,
    generate_recovery_codes,
    consume_recovery_code,
)

router = APIRouter()

LINK_INVALID_DETAIL = (
    "Link inválido, expirado ou já utilizado. Solicite um novo acesso."
)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, description="E-mail corporativo @claro.com.br")


class VerifyConfirmRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Token do magic link")


class CreateLocalUserRequest(BaseModel):
    email: str = Field(..., min_length=3, description="E-mail corporativo @claro.com.br")
    full_name: str = Field(..., min_length=1, description="Nome completo do usuário")
    role: Literal["user", "admin"] = "user"
    username: Optional[str] = Field(
        None,
        min_length=1,
        description="Opcional; se omitido, deriva da parte local do e-mail",
    )


class TwoFAConfirmSetupRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, description="Código TOTP de 6 dígitos")


class TwoFAVerifyRequest(BaseModel):
    code: Optional[str] = Field(None, min_length=6, max_length=6, description="Código TOTP")
    recovery_code: Optional[str] = Field(None, description="Código de recuperação")


def _public_user(user: dict) -> dict:
    """Campos públicos de um usuário local (sem hashed_password e segredos TOTP)."""
    return {
        "username": user["username"],
        "full_name": user.get("full_name"),
        "email": user.get("email"),
        "role": user.get("role"),
        "active": user.get("active", False),
        "totp_enabled": user.get("totp_enabled", False),
    }


def _derive_unique_username(base: str, users: list) -> str:
    """Gera username único a partir da base (parte local do e-mail ou valor informado)."""
    cleaned = base.strip().lower()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível derivar um username válido do e-mail.",
        )
    existing = {(u.get("username") or "").strip().lower() for u in users}
    if cleaned not in existing:
        return cleaned
    n = 2
    while f"{cleaned}{n}" in existing:
        n += 1
    return f"{cleaned}{n}"


@router.post("/login")
async def login(payload: LoginRequest):
    """
    Solicita um magic link passwordless.
    Resposta sempre genérica — não revela se o e-mail existe.
    Domínio fora do permitido é rejeitado com 400.
    """
    email = payload.email.strip().lower()

    # Anti-spam de e-mail (Resend) e anti-enumeração: por destinatário e teto global
    check_rate_limit(f"login:{email}", max_hits=5, window_seconds=900)
    check_rate_limit("login:global", max_hits=60, window_seconds=60)

    if not is_allowed_email_domain(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Somente e-mails @{settings.ALLOWED_EMAIL_DOMAIN} são permitidos.",
        )

    user = find_user_by_email(email)
    if user:
        raw_token = create_magic_link_token(username=user["username"], purpose="login")
        try:
            send_magic_link(to_email=email, raw_token=raw_token)
        except RuntimeError as exc:
            # Usuário já encontrado — 502 com detalhe acionável (ex.: domínio Resend).
            # E-mails desconhecidos continuam no 200 genérico acima (não entra aqui).
            detail = str(exc).strip() or (
                "Não foi possível enviar o e-mail de acesso. Tente novamente mais tarde."
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=detail,
            ) from exc

    return {
        "message": (
            "Se o e-mail estiver cadastrado, você receberá um link de acesso "
            f"em alguns instantes. O link é válido por {settings.MAGIC_LINK_EXPIRE_MINUTES} minutos."
        )
    }


def _login_url(**query: str) -> str:
    """Monta URL do frontend /login com query string."""
    base = settings.APP_BASE_URL.rstrip("/") + "/login"
    if not query:
        return base
    parts = [f"{k}={quote(v, safe='')}" for k, v in query.items()]
    return f"{base}?{'&'.join(parts)}"


@router.get("/verify")
async def verify_magic_link_landing(token: str = ""):
    """
    Landing do magic link — redireciona para o frontend com o token na query.
    Válido por 10 minutos (permite múltiplos usos no período).
    """
    username = peek_magic_link_token(token, purpose="login") if token else None
    if not username:
        return RedirectResponse(
            url=_login_url(error="invalid_link"),
            status_code=status.HTTP_302_FOUND,
        )

    users = load_users()
    user = next((u for u in users if u["username"] == username and u.get("active")), None)
    if not user:
        return RedirectResponse(
            url=_login_url(error="invalid_link"),
            status_code=status.HTTP_302_FOUND,
        )

    return RedirectResponse(
        url=_login_url(token=token),
        status_code=status.HTTP_302_FOUND,
    )


@router.head("/verify")
async def verify_magic_link_head(token: str = ""):
    """
    HEAD de scanners (ex.: Microsoft Safe Links) — valida se o link ainda está ativo.
    204 se o link ainda é utilizável; 404 caso contrário.
    """
    username = peek_magic_link_token(token, purpose="login") if token else None
    if not username:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    users = load_users()
    user = next((u for u in users if u["username"] == username and u.get("active")), None)
    if not user:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/verify")
async def confirm_magic_link(payload: VerifyConfirmRequest):
    """
    Autentica via magic link (válido por 10 minutos, permite múltiplos usos).

    NÃO seta sessão completa. Em vez disso:
    - Seta cookie pré-autenticação (5 min, scope="2fa")
    - Retorna status de 2FA:
      - "totp_required": usuário já tem 2FA configurada
      - "totp_setup_required": primeiro login, precisa configurar 2FA
    """
    username = consume_magic_link_token(payload.token, purpose="login")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=LINK_INVALID_DETAIL,
        )

    users = load_users()
    user = next((u for u in users if u["username"] == username and u.get("active")), None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=LINK_INVALID_DETAIL,
        )

    # Determinar próximo passo 2FA
    totp_enabled = user.get("totp_enabled", False)
    status_2fa = "totp_required" if totp_enabled else "totp_setup_required"

    # Criar token pré-autenticação
    pre_auth_token = create_pre_auth_token(username)

    response = JSONResponse(
        content={
            "status": status_2fa,
            "message": f"Próximo passo: {'confirme seu código TOTP' if totp_enabled else 'configure 2FA'}.",
        }
    )
    set_pre_auth_cookie(response, pre_auth_token)
    return response



@router.post("/logout")
async def logout(response: Response):
    """Remove os cookies de sessão e pré-autenticação do navegador."""
    clear_session_cookie(response)
    clear_pre_auth_cookie(response)
    return {"message": "Sessão encerrada"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado pela sessão atual."""
    return current_user


# ─── 2FA (TOTP) ────────────────────────────────────────────────────────────

@router.post("/2fa/setup")
async def setup_totp(
    pre_auth_user: dict = Depends(get_pre_auth_user),
):
    """
    Inicia setup de 2FA (TOTP).

    Requer pré-autenticação (cookie pre_auth_token com scope="2fa").
    Se usuário já tem 2FA ativo, retorna 400.
    Senão, gera segredo, o armazena criptografado em totp_pending_enc,
    e retorna otpauth_uri + secret para o frontend.
    """
    username = pre_auth_user["username"]

    # Carregar usuário completo (com campos sensíveis) para verificação
    users = load_users()
    user = next((u for u in users if u["username"] == username), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    # Rejeitar se já tem 2FA ativo
    if user.get("totp_enabled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA já está ativado para este usuário. Use /2fa/reset para começar novamente."
        )

    # Gerar segredo
    secret = generate_secret()
    encrypted_secret = encrypt_secret(secret)

    # Armazenar em totp_pending_enc (ainda não ativo)
    user["totp_pending_enc"] = encrypted_secret
    save_users(users)

    # Gerar URI para QR code
    uri = provisioning_uri(username, secret)

    return {
        "otpauth_uri": uri,
        "secret": secret,
        "message": "Escaneie o QR code ou entre manualmente a chave."
    }


@router.post("/2fa/confirm-setup")
async def confirm_setup_totp(
    payload: TwoFAConfirmSetupRequest,
    pre_auth_user: dict = Depends(get_pre_auth_user),
    response: Response = None,
):
    """
    Confirma setup de 2FA.

    Valida código TOTP contra segredo pendente (totp_pending_enc).
    Se válido:
    - Move pending -> active (totp_secret_enc)
    - Marca totp_enabled = True
    - Gera 10 recovery codes (hashes armazenados)
    - Emite sessão completa (access_token com mfa=true)
    - Limpa pre_auth cookie
    - Retorna recovery codes (exibidos uma vez)

    Rate limit: 5 tentativas / 15 min por usuário.
    """
    username = pre_auth_user["username"]

    # Rate limit
    check_rate_limit(f"2fa:{username}", max_hits=5, window_seconds=900)

    # Carregar usuário
    users = load_users()
    user = next((u for u in users if u["username"] == username), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    # Verificar se já está ativo
    if user.get("totp_enabled"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA já está ativo.")

    # Verificar se tem segredo pendente
    if not user.get("totp_pending_enc"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhuma configuração de 2FA pendente. Use /2fa/setup primeiro."
        )

    # Validar código contra pending secret
    if not verify_code(user, payload.code, secret_field="totp_pending_enc"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código inválido.")

    # Sucesso: move pending -> active
    user["totp_secret_enc"] = user.pop("totp_pending_enc")
    user["totp_enabled"] = True
    # totp_last_step já foi gravado por verify_code: não resetar (anti-replay do código de setup)

    # Gerar recovery codes
    plain_codes, hashed_codes = generate_recovery_codes(n=10)
    user["totp_recovery_hashes"] = hashed_codes

    # Salvar usuário
    save_users(users)

    # Emitir sessão completa
    access_token = create_access_token(data={"sub": username, "mfa": True})
    set_session_cookie(response, access_token)
    clear_pre_auth_cookie(response)

    return {
        "user": sanitize_user(user),
        "recovery_codes": plain_codes,
        "message": "2FA ativado com sucesso! Salve os códigos de recuperação em um local seguro."
    }


@router.post("/2fa/verify")
async def verify_totp(
    payload: TwoFAVerifyRequest,
    pre_auth_user: dict = Depends(get_pre_auth_user),
    response: Response = None,
):
    """
    Verifica código TOTP ou recovery code.

    Requer exatamente um de: code (TOTP) ou recovery_code.
    Se válido, emite sessão completa (access_token com mfa=true).

    Rate limit:
    - Por usuário: 5 tentativas / 15 min
    - Global: 60 tentativas / 1 min

    Erros genéricos (401) para não vazar informações.
    """
    username = pre_auth_user["username"]

    # Validar payload
    if (payload.code and payload.recovery_code) or (not payload.code and not payload.recovery_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forneça exatamente um de: code ou recovery_code."
        )

    # Rate limit
    check_rate_limit(f"2fa:{username}", max_hits=5, window_seconds=900)
    check_rate_limit("2fa:global", max_hits=60, window_seconds=60)

    # Carregar usuário
    users = load_users()
    user = next((u for u in users if u["username"] == username), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código inválido.")

    if not user.get("totp_enabled"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código inválido.")

    valid = False

    # Tentar validar código TOTP
    if payload.code:
        valid = verify_code(user, payload.code, secret_field="totp_secret_enc")
        if valid:
            save_users(users)  # Salvar totp_last_step atualizado
    # Tentar consumir recovery code
    elif payload.recovery_code:
        valid = consume_recovery_code(username, payload.recovery_code)

    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código inválido.")

    # Sucesso: emitir sessão
    access_token = create_access_token(data={"sub": username, "mfa": True})
    set_session_cookie(response, access_token)
    clear_pre_auth_cookie(response)

    # Recarregar usuário sanitizado para retorno
    users = load_users()
    user = next((u for u in users if u["username"] == username), None)

    return {
        "user": sanitize_user(user),
        "message": "Autenticação bem-sucedida."
    }


# ─── Gestão de usuários locais (somente admin) ─────────────────────────────

@router.get("/users")
async def list_local_users(admin: dict = Depends(require_admin)):
    """Lista os usuários locais da ferramenta (sem o hash de senha). Somente admin."""
    users = load_users()
    return {"users": [_public_user(u) for u in users]}


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_local_user(
    payload: CreateLocalUserRequest,
    admin: dict = Depends(require_admin),
):
    """
    Cadastra um usuário local da plataforma. Login continua via magic link;
    hashed_password é gerado aleatoriamente só para manter o schema de users.json.
    """
    email = payload.email.strip().lower()
    full_name = payload.full_name.strip()
    if not full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome completo é obrigatório.",
        )

    if not is_allowed_email_domain(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Somente e-mails @{settings.ALLOWED_EMAIL_DOMAIN} são permitidos.",
        )

    users = load_users()
    if any((u.get("email") or "").strip().lower() == email for u in users):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário com este e-mail.",
        )

    if payload.username and payload.username.strip():
        username = payload.username.strip().lower()
        if any((u.get("username") or "").strip().lower() == username for u in users):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um usuário com este username.",
            )
    else:
        local_part = email.rsplit("@", 1)[0]
        username = _derive_unique_username(local_part, users)

    new_user = {
        "username": username,
        "full_name": full_name,
        "email": email,
        "hashed_password": hash_password(generate_password()),
        "role": payload.role,
        "active": True,
    }
    users.append(new_user)
    save_users(users)

    return _public_user(new_user)


@router.delete("/users/{username}")
async def delete_local_user(username: str, admin: dict = Depends(require_admin)):
    """
    Remove um usuário local da plataforma (users.json). Somente admin.
    Não permite excluir a si mesmo nem o último admin restante.
    """
    needle = username.strip().lower()
    users = load_users()
    idx = next(
        (i for i, u in enumerate(users) if (u.get("username") or "").strip().lower() == needle),
        None,
    )
    if idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    target = users[idx]
    admin_username = (admin.get("username") or "").strip().lower()
    if (target.get("username") or "").strip().lower() == admin_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode excluir o próprio usuário da sessão atual.",
        )

    if target.get("role") == "admin":
        admin_count = sum(1 for u in users if u.get("role") == "admin")
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível excluir o último administrador da plataforma.",
            )

    removed = users.pop(idx)
    save_users(users)
    return {
        "message": f"Usuário {removed.get('username')} removido.",
        "username": removed.get("username"),
    }


@router.post("/users/{username}/2fa/reset")
async def admin_reset_2fa(username: str, admin: dict = Depends(require_admin)):
    """
    Reseta 2FA de um usuário (admin only).

    Remove campos TOTP:
    - totp_secret_enc
    - totp_pending_enc
    - totp_last_step
    - totp_recovery_hashes
    - totp_enabled

    Restrições:
    - Não permite reset na própria conta (admin.username != username)
    - Retorna 404 se usuário não existe
    """
    needle = username.strip().lower()
    admin_username = (admin.get("username") or "").strip().lower()

    if needle == admin_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode resetar sua própria 2FA.",
        )

    users = load_users()
    user = next((u for u in users if (u.get("username") or "").strip().lower() == needle), None)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    # Limpar campos TOTP (mesmo que _não_ estejam presentes)
    user.pop("totp_secret_enc", None)
    user.pop("totp_pending_enc", None)
    user.pop("totp_last_step", None)
    user.pop("totp_recovery_hashes", None)
    user.pop("totp_enabled", None)

    save_users(users)

    return {
        "message": f"2FA de {user.get('username')} foi resetada.",
        "username": user.get("username"),
    }
