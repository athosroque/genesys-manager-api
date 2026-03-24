import httpx
from pydantic import BaseModel
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from auth_local import get_current_user
from config import BASE_URL, DIVISION_ID, ROLE_ID
from auth import get_token, h

router = APIRouter()

class MigrationRequest(BaseModel):
    user_id: str
    op: str  # "1", "2" ou "3"
    group_id: Optional[str] = None

@router.post("/run")
async def run_migration(payload: MigrationRequest, current_user: dict = Depends(get_current_user)):
    """
    Executa a migração de um usuário baseada no modo ("1", "2", "3").
    Modo 1: Divisão (Home) + Role (Employee)
    Modo 2: Adicionar ao Grupo
    Modo 3: Divisão + Role + Grupo
    """
    user_id = payload.user_id.strip("{}")
    
    token = await get_token()
    headers = h(token)
    steps = []
    
    async with httpx.AsyncClient() as client:
        # Passos A e B: modos "1" e "3"
        if payload.op in ["1", "3"]:
            # Passo A: Mover para Divisão Home
            url_div = f"{BASE_URL}/authorization/divisions/{DIVISION_ID}/objects/USER"
            body_div = [user_id]
            resp_div = await client.post(url_div, json=body_div, headers=headers)
            
            if resp_div.status_code >= 400:
                steps.append({"label": "Mover para Divisão Home", "status": "error", "detail": resp_div.text})
            else:
                steps.append({"label": "Mover para Divisão Home", "status": "ok", "detail": "Divisão atualizada."})
                
            # Passo B: Atribuir Role + Division
            url_role = f"{BASE_URL}/authorization/subjects/{user_id}/bulkadd"
            body_role = {"grants": [{"roleId": ROLE_ID, "divisionId": DIVISION_ID}]}
            resp_role = await client.post(url_role, json=body_role, headers=headers)
            
            if resp_role.status_code >= 400:
                steps.append({"label": "Atribuir Role", "status": "error", "detail": resp_role.text})
            else:
                steps.append({"label": "Atribuir Role", "status": "ok", "detail": "Role atribuída."})
                
        # Passo C: Modos "2" e "3"
        if payload.op in ["2", "3"]:
            if not payload.group_id:
                steps.append({"label": "Adicionar ao Grupo", "status": "error", "detail": "group_id não informado."})
            else:
                group_id = payload.group_id.strip("{}")
                
                # Tenta adicionar o usuário ao grupo. Usa uma função auxiliar para retry.
                async def assign_group(client, gid, uid, headers, attempt=1):
                    # 1. Pega a versão
                    resp_group = await client.get(f"{BASE_URL}/groups/{gid}", headers=headers)
                    if resp_group.status_code >= 400:
                        return {"status": "error", "detail": f"Erro obtendo versão do grupo: {resp_group.text}"}
                    
                    version = resp_group.json().get("version", 1)
                    
                    # 2. Adiciona o membro
                    resp_add = await client.post(
                        f"{BASE_URL}/groups/{gid}/members", 
                        json={"memberIds": [uid], "version": version}, 
                        headers=headers
                    )
                    
                    if resp_add.status_code in [200, 202, 204]:
                        return {"status": "ok", "detail": "Adicionado ao grupo."}
                    
                    # 3. Retry no 409
                    if resp_add.status_code == 409:
                        if attempt == 1:
                            return await assign_group(client, gid, uid, headers, attempt=2)
                        else:
                            return {"status": "skip", "detail": "Usuário já era membro (ou conflito persiste)."}
                            
                    return {"status": "error", "detail": f"Falha ao adicionar: {resp_add.text}"}
                
                result_group = await assign_group(client, group_id, user_id, headers)
                steps.append({"label": "Adicionar ao Grupo", "status": result_group["status"], "detail": result_group["detail"]})

    return {"steps": steps}
