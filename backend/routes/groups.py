import httpx
from fastapi import APIRouter, HTTPException, Depends
from config import BASE_URL
from auth import get_token, h
from auth_local import get_current_user

router = APIRouter()

@router.delete("/{group_id}/members/{user_id}")
async def remove_user_from_group(group_id: str, user_id: str, current_user: dict = Depends(get_current_user)):
    """
    Remove o usuário do grupo especificado.
    Importante: A API exige que o user_id seja passado como query param 'ids'.
    """
    user_id = user_id.strip("{}")
    group_id = group_id.strip("{}")
    
    token = await get_token()
    headers = h(token)
    
    async with httpx.AsyncClient() as client:
        # ATENÇÃO CRÍTICA: ids deve ser query param.
        url = f"{BASE_URL}/groups/{group_id}/members?ids={user_id}"
        
        response = await client.delete(url, headers=headers)
        
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=f"Erro ao remover do grupo Genesys: {response.text}")
            
        return {"success": True, "http_code": response.status_code}
