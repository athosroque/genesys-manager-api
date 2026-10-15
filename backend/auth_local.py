import json
import os
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request, Response, Depends
from config import settings

# ─── Configuração de Criptografia ───────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── Persistência em Arquivo ───────────────────────────────────────────────
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

def load_users() -> List[dict]:
    """Lê o arquivo users.json e retorna a lista de usuários."""
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("users", [])
    except (json.JSONDecodeError, IOError):
        return []

def save_users(users: List[dict]) -> None:
    """Persiste a lista de usuários de volta em users.json."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": users}, f, ensure_ascii=False, indent=2)

# ─── Schema users.json (hashed_password) ───────────────────────────────────
# Login é passwordless (magic link). hash_password/generate_password só
# preenchem o campo legado hashed_password no create admin — não há fluxo de senha.

def hash_password(plain_password: str) -> str:
    """Gera hash bcrypt (campo hashed_password do schema JSON)."""
    return pwd_context.hash(plain_password)

def generate_password(length: int = 14) -> str:
    """Gera string aleatória forte para popular hashed_password no cadastro."""
    symbols = "!@#$%*_-+="
    alphabet = string.ascii_letters + string.digits + symbols
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in symbols for c in pwd)
        ):
            return pwd

# ─── Domínio e busca por e-mail ────────────────────────────────────────────
def is_allowed_email_domain(email: str) -> bool:
    """Retorna True se o e-mail pertence ao domínio permitido (ex.: claro.com.br)."""
    if not email or "@" not in email:
        return False
    domain = email.rsplit("@", 1)[-1].strip().lower()
    return domain == settings.ALLOWED_EMAIL_DOMAIN.lower()


def sanitize_user(user: dict) -> dict:
    """
    Remove campos sensíveis do usuário (senha e segredos TOTP).
    Retorna cópia sem: hashed_password, totp_secret_enc, totp_pending_enc,
    totp_last_step, totp_recovery_hashes.
    Mantém totp_enabled (publicável).
    """
    user_data = user.copy()
    user_data.pop("hashed_password", None)
    user_data.pop("totp_secret_enc", None)
    user_data.pop("totp_pending_enc", None)
    user_data.pop("totp_last_step", None)
    user_data.pop("totp_recovery_hashes", None)
    return user_data


def find_user_by_email(email: str) -> Optional[dict]:
    """
    Localiza usuário ativo pelo e-mail (case-insensitive).
    Retorna cópia sanitizada, ou None.
    """
    if not email:
        return None
    needle = email.strip().lower()
    users = load_users()
    user = next(
        (
            u for u in users
            if (u.get("email") or "").strip().lower() == needle and u.get("active", False)
        ),
        None,
    )
    if not user:
        return None
    return sanitize_user(user)


# ─── Gestão de Tokens JWT ─────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Gera um JWT assinado com tempo de expiração.

    Para sessão completa (pós-2FA), caller deve adicionar "mfa": True em data.
    Tokens com scope (como pré-autenticação) são rejeitados em get_current_user.
    """
    to_encode = data.copy()

    # Adicionar mfa=False como padrão se não especificado
    if "mfa" not in to_encode:
        to_encode["mfa"] = False

    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta
        else timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def set_session_cookie(response: Response, access_token: str) -> None:
    """Define o cookie HttpOnly da sessão (prod vs. dev)."""
    max_age = settings.cookie_max_age
    if settings.ENVIRONMENT == "production":
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=max_age,
            path="/",
            domain=settings.COOKIE_DOMAIN or None,
        )
    else:
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="lax",
            max_age=max_age,
            path="/",
            secure=False,
        )


def clear_session_cookie(response: Response) -> None:
    """
    Remove o cookie de sessão com os mesmos atributos de set_session_cookie.
    Sem domain/secure/samesite alinhados, o browser pode ignorar o delete em produção.
    """
    if settings.ENVIRONMENT == "production":
        response.delete_cookie(
            key="access_token",
            path="/",
            domain=settings.COOKIE_DOMAIN or None,
            secure=True,
            httponly=True,
            samesite="none",
        )
    else:
        response.delete_cookie(
            key="access_token",
            path="/",
            secure=False,
            httponly=True,
            samesite="lax",
        )


def create_pre_auth_token(username: str) -> str:
    """
    Cria um JWT pré-autenticação para 2FA (validação de código TOTP).

    Carrega:
    - sub: username
    - scope: "2fa" (indica pré-autenticação)
    - exp: 5 minutos

    Retorna token JWT assinado.
    """
    data = {
        "sub": username,
        "scope": "2fa",
    }
    expires_delta = timedelta(minutes=5)
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def set_pre_auth_cookie(response: Response, pre_auth_token: str) -> None:
    """Define o cookie pré-autenticação com mesmos atributos de set_session_cookie."""
    max_age = 300  # 5 minutos
    if settings.ENVIRONMENT == "production":
        response.set_cookie(
            key="pre_auth_token",
            value=pre_auth_token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=max_age,
            path="/",
            domain=settings.COOKIE_DOMAIN or None,
        )
    else:
        response.set_cookie(
            key="pre_auth_token",
            value=pre_auth_token,
            httponly=True,
            samesite="lax",
            max_age=max_age,
            path="/",
            secure=False,
        )


def clear_pre_auth_cookie(response: Response) -> None:
    """Remove o cookie pré-autenticação com mesmos atributos de set_pre_auth_cookie."""
    if settings.ENVIRONMENT == "production":
        response.delete_cookie(
            key="pre_auth_token",
            path="/",
            domain=settings.COOKIE_DOMAIN or None,
            secure=True,
            httponly=True,
            samesite="none",
        )
    else:
        response.delete_cookie(
            key="pre_auth_token",
            path="/",
            secure=False,
            httponly=True,
            samesite="lax",
        )


# ─── Injeção de Dependência (FastAPI) ──────────────────────────────────────
async def get_current_user(request: Request, response: Response) -> dict:
    """
    Dependency para extrair o usuário logado a partir do cookie 'access_token'.

    Rejeita tokens com:
    - scope: Invalida pré-autenticação (use get_pre_auth_user em /2fa/*)
    - mfa: false ou ausente: Sessão sem 2FA (força relogin)

    Em sucesso, renova JWT e cookie (sliding session de 48h).
    Lança 401 Unauthorized se inválido, ausente, expirado ou sem mfa=true.
    """
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tokens de acesso não encontrados. Por favor, realize o login.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Decodifica o payload
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

        # Rejeita tokens com scope (pré-autenticação não é sessão completa)
        if payload.get("scope"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de pré-autenticação. Complete o 2FA."
            )

        # Rejeita tokens sem mfa=true (força relogin)
        if not payload.get("mfa"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessão expirada ou sem autenticação de múltiplos fatores. Realize login novamente."
            )

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado ou corrompido.")

    # Verifica se o usuário ainda existe e está ativo no JSON
    users = load_users()
    user = next((u for u in users if u["username"] == username and u["active"]), None)

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado ou inativo.")

    # Sanitize user data
    user_data = sanitize_user(user)

    # Sliding session: reemite JWT com mfa=true e reseta o cookie por mais JWT_EXPIRE_MINUTES
    renewed = create_access_token(data={"sub": username, "mfa": True})
    set_session_cookie(response, renewed)

    return user_data

async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency que restringe a rota a usuários com role 'admin'."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores.",
        )
    return current_user


async def get_pre_auth_user(request: Request) -> dict:
    """
    Dependency para extrair usuário pré-autenticado (após magic link, antes de 2FA).

    Lê cookie 'pre_auth_token' que deve:
    - Ter scope="2fa"
    - Ter sub (username)
    - Estar válido (não expirado)
    - Usuário deve estar ativo

    Retorna usuário sanitizado.
    Lança 401 se token inválido, ausente, expirado ou usuário inativo.
    """
    token = request.cookies.get("pre_auth_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pré-autenticação expirada. Realize login novamente.",
        )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        scope: str = payload.get("scope")

        if username is None or scope != "2fa":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de pré-autenticação inválido."
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pré-autenticação expirada ou corrompida."
        )

    # Verificar se usuário existe e está ativo
    users = load_users()
    user = next((u for u in users if u["username"] == username and u.get("active")), None)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo."
        )

    return sanitize_user(user)


def get_token_from_cookie(request: Request) -> str:
    """Extrai apenas a string do token do cookie seguro."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado.")
    return token
