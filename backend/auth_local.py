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


def find_user_by_email(email: str) -> Optional[dict]:
    """
    Localiza usuário ativo pelo e-mail (case-insensitive).
    Retorna cópia sem hashed_password, ou None.
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
    user_data = user.copy()
    user_data.pop("hashed_password", None)
    return user_data


# ─── Gestão de Tokens JWT ─────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Gera um JWT assinado com tempo de expiração."""
    to_encode = data.copy()
    
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


# ─── Injeção de Dependência (FastAPI) ──────────────────────────────────────
async def get_current_user(request: Request, response: Response) -> dict:
    """
    Dependency para extrair o usuário logado a partir do cookie 'access_token'.
    Em caso de sucesso, renova o JWT e o cookie (sliding session de 48h).
    Lança 401 Unauthorized se o token for inválido, ausente ou expirado.
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
            
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado ou corrompido.")
        
    # Verifica se o usuário ainda existe e está ativo no JSON
    users = load_users()
    user = next((u for u in users if u["username"] == username and u["active"]), None)
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado ou inativo.")
        
    user_data = user.copy()
    user_data.pop("hashed_password", None)

    # Sliding session: reemite JWT e reseta o cookie por mais JWT_EXPIRE_MINUTES
    renewed = create_access_token(data={"sub": username})
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

def get_token_from_cookie(request: Request) -> str:
    """Extrai apenas a string do token do cookie seguro."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado.")
    return token
