import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request
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

# ─── Utilitários de Senha ──────────────────────────────────────────────────
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha plana coincide com o hash bcrypt."""
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)

# ─── Lógica de Autenticação ───────────────────────────────────────────────
def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Autentica o usuário baseado no arquivo JSON.
    Retorna o dicionário do usuário (sem o hash) ou None.
    """
    users = load_users()
    user = next((u for u in users if u["username"] == username), None)
    
    if not user:
        return None
    
    if not user.get("active", False):
        return None
        
    if not verify_password(password, user.get("hashed_password", "")):
        return None
        
    # Retorna cópia sem a senha
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

# ─── Injeção de Dependência (FastAPI) ──────────────────────────────────────
async def get_current_user(request: Request) -> dict:
    """
    Dependency para extrair o usuário logado a partir do cookie 'access_token'.
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
    return user_data

def get_token_from_cookie(request: Request) -> str:
    """Extrai apenas a string do token do cookie seguro."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado.")
    return token
