import time
import httpx
from fastapi import HTTPException
from config import settings, AUTH_URL

_token: str | None = None
_expires_at: float = 0.0

async def get_token() -> str:
    global _token, _expires_at
    
    # Se o token existir e faltar mais de 60 segundos para espirar
    if _token and time.time() < (_expires_at - 60):
        return _token

    client_id = settings.GENESYS_CLIENT_ID
    client_secret = settings.GENESYS_CLIENT_SECRET
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Credenciais Genesys (CLIENT_ID / CLIENT_SECRET) não configuradas no .env")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                AUTH_URL,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret)
            )
            response.raise_for_status()
            data = response.json()
            
            _token = data.get("access_token")
            # a Genesys geralmente retorna expires_in em segundos
            expires_in = data.get("expires_in", 1800)
            _expires_at = time.time() + expires_in
            
            return _token
            
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502, 
            detail=f"Falha na autenticação com Genesys: {str(e)}"
        )

def h(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
