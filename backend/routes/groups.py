import httpx
from fastapi import APIRouter, HTTPException, Depends
from config import BASE_URL
from auth import get_token, h
from auth_local import get_current_user

router = APIRouter()

PAGE_SIZE = 100
MAX_PAGES = 25  # ~2500 grupos: folga enorme; evita varredura sem fim se a org for gigante


@router.get("")
async def list_groups(current_user: dict = Depends(get_current_user)):
    """
    Mapa {id, name} de todos os grupos da org (paginado GET {BASE_URL}/groups).
    Usado para resolver os chips de grupo da Trilha de Auditoria de uma vez, sem
    lookup por UUID. Com teto de páginas (flag `truncated` se estourar).
    """
    token = await get_token()
    headers = h(token)

    groups: list[dict] = []
    truncated = False

    async with httpx.AsyncClient(timeout=30) as client:
        for page_number in range(1, MAX_PAGES + 1):
            url = f"{BASE_URL}/groups?pageSize={PAGE_SIZE}&pageNumber={page_number}"
            response = await client.get(url, headers=headers)

            if response.status_code >= 400:
                # Não quebra a timeline: devolve o que já coletou + aviso.
                return {
                    "groups": groups,
                    "warning": f"erro ao listar grupos Genesys: {response.text[:200]}",
                }

            data = response.json()
            entities = data.get("entities", [])
            groups.extend(
                {"id": e.get("id"), "name": e.get("name")}
                for e in entities
                if e.get("id")
            )

            page_count = data.get("pageCount", 1)
            if not entities or page_number >= page_count:
                break
            if page_number == MAX_PAGES:
                truncated = True

    return {"groups": groups, "truncated": truncated}


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
