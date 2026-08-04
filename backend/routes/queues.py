import httpx
from fastapi import APIRouter, HTTPException, Depends
from config import BASE_URL
from auth import get_token, h
from auth_local import get_current_user

router = APIRouter()

PAGE_SIZE = 100
MAX_PAGES = 25  # ~2500 filas: folga enorme; evita varredura sem fim


@router.get("")
async def list_queues(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Mapa {id, name} de todas as filas da org (paginado GET {BASE_URL}/routing/queues).
    Mesmo padrão de /roles e /groups — usado para resolver busca por nome de
    fila na Trilha de Auditoria sem lookup individual por UUID.
    """
    token = await get_token()
    headers = h(token)

    queues: list[dict] = []
    truncated = False

    async with httpx.AsyncClient(timeout=30) as client:
        for page_number in range(1, MAX_PAGES + 1):
            url = f"{BASE_URL}/routing/queues?pageSize={PAGE_SIZE}&pageNumber={page_number}"
            response = await client.get(url, headers=headers)

            if response.status_code >= 400:
                # Não quebra a busca: devolve o que já coletou + aviso.
                return {
                    "queues": queues,
                    "warning": f"erro ao listar filas Genesys: {response.text[:200]}",
                }

            data = response.json()
            entities = data.get("entities", [])
            queues.extend(
                {"id": e.get("id"), "name": e.get("name")}
                for e in entities
                if e.get("id")
            )

            page_count = data.get("pageCount", 1)
            if not entities or page_number >= page_count:
                break
            if page_number == MAX_PAGES:
                truncated = True

    return {"queues": queues, "truncated": truncated}


@router.delete("/user/{user_id}/all")
async def delete_user_from_all_queues(user_id: str, current_user: dict = Depends(get_current_user)):
    """
    Remove o usuário de todas as filas em que ele está configurado.
    """
    user_id = user_id.strip("{}")
    token = await get_token()
    headers = h(token)
    
    async with httpx.AsyncClient() as client:
        # 1. Buscar filas atuais
        url_search = f"{BASE_URL}/users/{user_id}/queues"
        response_search = await client.get(url_search, headers=headers)
        
        if response_search.status_code >= 400:
            raise HTTPException(status_code=response_search.status_code, detail=f"Erro ao buscar filas Genesys: {response_search.text}")
            
        data = response_search.json()
        entities = data.get("entities", [])
        
        results = []
        
        # 2. Para cada fila, remover o usuário
        for queue in entities:
            queue_id = queue.get("id")
            queue_name = queue.get("name")
            
            url_delete = f"{BASE_URL}/routing/queues/{queue_id}/members/{user_id}"
            response_delete = await client.delete(url_delete, headers=headers)
            
            if response_delete.status_code in [200, 202, 204]:
                status = "removed"
            elif response_delete.status_code == 404:
                status = "skip" # Já não era membro
            else:
                status = "error"
                
            results.append({
                "queue_id": queue_id,
                "queue_name": queue_name,
                "status": status,
                "http_code": response_delete.status_code
            })
            
        return {"results": results}


@router.delete("/{queue_id}/member/{user_id}")
async def delete_user_from_queue(queue_id: str, user_id: str, current_user: dict = Depends(get_current_user)):
    """
    Remove o usuário de uma fila específica pelo ID da fila.
    """
    queue_id = queue_id.strip("{}")
    user_id  = user_id.strip("{}")
    
    token   = await get_token()
    headers = h(token)
    
    async with httpx.AsyncClient() as client:
        url = f"{BASE_URL}/routing/queues/{queue_id}/members/{user_id}"
        response = await client.delete(url, headers=headers)
        
        if response.status_code in [200, 202, 204]:
            return {"success": True, "status": "removed"}
        elif response.status_code == 404:
            return {"success": True, "status": "skip"}
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erro ao remover da fila: {response.text}"
            )
