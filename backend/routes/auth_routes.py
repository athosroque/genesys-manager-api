from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from auth_local import (
    create_access_token,
    get_current_user,
    require_admin,
    load_users,
    save_users,
    hash_password,
    generate_password,
    find_user_by_email,
    is_allowed_email_domain,
    set_session_cookie,
    clear_session_cookie,
)
from config import settings
from email_service import send_magic_link
from token_store import create_magic_link_token, consume_magic_link_token

router = APIRouter()


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, description="E-mail corporativo @claro.com.br")


class CreateLocalUserRequest(BaseModel):
    email: str = Field(..., min_length=3, description="E-mail corporativo @claro.com.br")
    full_name: str = Field(..., min_length=1, description="Nome completo do usuário")
    role: Literal["user", "admin"] = "user"
    username: Optional[str] = Field(
        None,
        min_length=1,
        description="Opcional; se omitido, deriva da parte local do e-mail",
    )


def _public_user(user: dict) -> dict:
    """Campos públicos de um usuário local (sem hashed_password)."""
    return {
        "username": user["username"],
        "full_name": user.get("full_name"),
        "email": user.get("email"),
        "role": user.get("role"),
        "active": user.get("active", False),
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


@router.get("/verify")
async def verify_magic_link(token: str):
    """
    Consome o magic link (uso único, 10 min), seta cookie JWT (48h idle)
    e redireciona para o frontend.
    """
    username = consume_magic_link_token(token, purpose="login")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link inválido, expirado ou já utilizado. Solicite um novo acesso.",
        )

    users = load_users()
    user = next((u for u in users if u["username"] == username and u.get("active")), None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link inválido, expirado ou já utilizado. Solicite um novo acesso.",
        )

    access_token = create_access_token(data={"sub": username})
    redirect_url = settings.APP_BASE_URL.rstrip("/") + "/"
    redirect = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    set_session_cookie(redirect, access_token)
    return redirect



@router.post("/logout")
async def logout(response: Response):
    """Remove o cookie de sessão do navegador (mesmos atributos do set)."""
    clear_session_cookie(response)
    return {"message": "Sessão encerrada"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado pela sessão atual."""
    return current_user


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
