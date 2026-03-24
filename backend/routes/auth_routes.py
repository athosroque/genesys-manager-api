from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel
from auth_local import (
    authenticate_user, 
    create_access_token, 
    get_current_user
)
from config import settings

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(payload: LoginRequest, response: Response):
    """
    Realiza o login local. Se as credenciais baterem com o users.json,
    gera um JWT e o define em um cookie seguro HttpOnly.
    """
    user = authenticate_user(payload.username, payload.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos."
        )
    
    # Gera o token JWT com o 'sub' (subject) sendo o username
    access_token = create_access_token(data={"sub": user["username"]})
    
    # Define o Cookie de forma condicional
    if settings.ENVIRONMENT == "production":
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,          # Obrigatório para samesite=none
            samesite="none",       # Permite cross-site em HTTPS/Cloudflare
            max_age=28800,         # 8 horas
            domain=settings.COOKIE_DOMAIN
        )
    else:
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="lax",
            max_age=28800,
            secure=False
        )
    
    return {
        "message": "Login realizado com sucesso",
        "user": user
    }

@router.post("/logout")
async def logout(response: Response):
    """Remove o cookie de sessão do navegador."""
    response.delete_cookie("access_token", samesite="lax")
    return {"message": "Sessão encerrada"}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado pela sessão atual."""
    return current_user
