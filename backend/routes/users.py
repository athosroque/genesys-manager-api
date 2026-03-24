import re
import httpx
from fastapi import APIRouter, HTTPException, Query, Depends
from config import BASE_URL, DOMAIN
from auth import get_token, h
from auth_local import get_current_user

router = APIRouter()

UUID_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

@router.get("/search")
async def search_user(q: str = Query(..., min_length=1, description="Matricula, e-mail ou UUID"), current_user: dict = Depends(get_current_user)):
    """
    Busca um usuário na Genesys Cloud dinamicamente por UUID, E-mail ou Matrícula.
    """
    token = await get_token()
    headers = h(token)
    
    async with httpx.AsyncClient() as client:
        # Caso A: UUID (Sanitiza caso venha com {chaves})
        q_clean = q.strip("{}")
        
        if UUID_REGEX.match(q_clean):
            # Expansão crucial para pegar nomes de grupos e roles
            url = f"{BASE_URL}/users/{q_clean}?expand=authorization,groups"
            response = await client.get(url, headers=headers)
            
            if response.status_code == 404:
                return {"found": False, "user": None}
                
            response.raise_for_status()
            userData = response.json()
            
            # ── RESOLUÇÃO DE NOMES DE GRUPOS ──
            user_groups_raw = userData.get("groups", [])
            full_groups = []
            
            for g_raw in user_groups_raw:
                g_id = g_raw.get("id")
                if not g_id: continue
                try:
                    g_resp = await client.get(f"{BASE_URL}/groups/{g_id}", headers=headers)
                    if g_resp.status_code == 200:
                        full_groups.append({"id": g_id, "name": g_resp.json().get("name", g_id)})
                    else:
                        full_groups.append({"id": g_id, "name": f"ID:{g_id[:8]}…"})
                except Exception:
                    full_groups.append({"id": g_id, "name": f"ID:{g_id[:8]}…"})
            
            userData["groups"] = full_groups
            return {"found": True, "user": userData}
            
        # Casos B e C: E-mail (contém @) ou Matrícula (não contém @)
        if "@" in q:
            email_search = q
        else:
            email_search = f"{q}{DOMAIN}"
            
        # Faz a busca POST exata pelo payload exigido pela Genesys
        payload = {
            "query": [
                {"fields": ["email"], "value": email_search, "type": "EXACT"},
                {"fields": ["state"], "values": ["active", "inactive"], "type": "EXACT", "operator": "OR"}
            ],
            # Importante: expand groups para trazer o nome e não só ID
            "expand": ["authorization", "groups"]
        }
        
        response = await client.post(f"{BASE_URL}/users/search", json=payload, headers=headers)
        
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=f"Erro na busca Genesys: {response.text}")
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            return {"found": False, "user": None}
            
        userData = results[0]
        
        # ── RESOLUÇÃO DE NOMES DE GRUPOS (Inspirado no Colab) ──
        # A busca retorna apenas IDs. Vamos buscar os nomes reais.
        user_groups_raw = userData.get("groups", [])
        full_groups = []
        
        for g_raw in user_groups_raw:
            g_id = g_raw.get("id")
            if not g_id: continue
            
            try:
                # Busca detalhe do grupo individual
                g_resp = await client.get(f"{BASE_URL}/groups/{g_id}", headers=headers)
                if g_resp.status_code == 200:
                    group_data = g_resp.json()
                    full_groups.append({
                        "id": g_id,
                        "name": group_data.get("name", f"ID:{g_id[:8]}…")
                    })
                else:
                    full_groups.append({"id": g_id, "name": f"ID:{g_id[:8]}…"})
            except Exception:
                full_groups.append({"id": g_id, "name": f"ID:{g_id[:8]}…"})
        
        # Substitui a lista de IDs pela lista com nomes
        userData["groups"] = full_groups
            
        return {"found": True, "user": userData}


from pydantic import BaseModel

class ReactivateRequest(BaseModel):
    version: int

@router.post("/{user_id}/reactivate")
async def reactivate_user(user_id: str, payload: ReactivateRequest, current_user: dict = Depends(get_current_user)):
    """
    Reativa um usuário inativo na Genesys Cloud. O campo version é obrigatório.
    """
    user_id = user_id.strip("{}")
    token = await get_token()
    headers = h(token)
    
    async with httpx.AsyncClient() as client:
        url = f"{BASE_URL}/users/{user_id}"
        
        # O PATCH exige o envio do state e da version atual do objeto
        body = {
            "state": "active",
            "version": payload.version
        }
        
        response = await client.patch(url, json=body, headers=headers)
        
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=f"Erro ao reativar usuário: {response.text}")
            
        return {"success": True, "user": response.json()}
        
@router.get("/{user_id}/queues")
async def get_user_queues(user_id: str, current_user: dict = Depends(get_current_user)):
    """
    Obtém todas as filas onde o usuário está configurado na plataforma.
    """
    # Sanitização: remove chaves caso o usuário tenha copiado literalmente do exemplo {uuid}
    user_id = user_id.strip("{}")
    
    token = await get_token()
    headers = h(token)
    
    async with httpx.AsyncClient() as client:
        url = f"{BASE_URL}/users/{user_id}/queues"
        response = await client.get(url, headers=headers)
        
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=f"Erro ao buscar filas Genesys: {response.text}")
            
        data = response.json()
        entities = data.get("entities", [])
        
        # Filtrar o objeto retornado para expor apenas os dados necessários no frontend
        queues = [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "joined": item.get("joined")
            }
            for item in entities
        ]
        
        return {"queues": queues}
