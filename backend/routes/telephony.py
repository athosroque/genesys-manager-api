import httpx
from fastapi import APIRouter, HTTPException, Query, Depends
from config import BASE_URL
from auth import get_token, h
from auth_local import get_current_user

router = APIRouter()

PHONES_URL = f"{BASE_URL}/telephony/providers/edges/phones"

PERMISSION_HINT = (
    "Integração sem permissão para gerenciar telefones (403 Forbidden). "
    "Requer permissão 'telephony:plugin:all' na role do OAuth Client."
)


def _phone_summary(p: dict) -> dict:
    site = p.get("site") or {}
    web_rtc_user = p.get("webRtcUser") or {}
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "state": p.get("state"),
        "site": {"id": site.get("id"), "name": site.get("name") or site.get("id")} if site else None,
        "web_rtc_user": (
            {"id": web_rtc_user.get("id"), "name": web_rtc_user.get("name")}
            if web_rtc_user
            else None
        ),
    }


@router.get("/phones/search")
async def search_phones(
    name: str = Query(..., min_length=2, description="Nome do ramal/telefone (aceita * como coringa)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Busca ramais (telefones) no Genesys Cloud pelo nome, para o operador escolher
    qual excluir quando o agente não tem ramal atribuído.
    """
    token = await get_token()
    headers = h(token)

    term = name.strip()
    if "*" not in term:
        term = f"*{term}*"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            PHONES_URL,
            params={"name": term, "pageSize": 25, "expand": "webRtcUser"},
            headers=headers,
        )

        if response.status_code == 403:
            raise HTTPException(status_code=403, detail=PERMISSION_HINT)
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=f"Erro ao buscar ramais Genesys: {response.text}")

        entities = response.json().get("entities", [])
        return {"results": [_phone_summary(p) for p in entities]}


@router.delete("/phones/{phone_id}")
async def delete_phone(phone_id: str, current_user: dict = Depends(get_current_user)):
    """
    Exclui um ramal (telefone) do Genesys Cloud. A estação vinculada ao telefone
    é removida junto pela própria plataforma.
    """
    phone_id = phone_id.strip("{}")
    token = await get_token()
    headers = h(token)

    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{PHONES_URL}/{phone_id}", headers=headers)

        if response.status_code in [200, 202, 204]:
            return {"success": True, "status": "deleted", "phone_id": phone_id}
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Ramal '{phone_id}' não encontrado no Genesys Cloud.")
        if response.status_code == 403:
            raise HTTPException(status_code=403, detail=PERMISSION_HINT)
        raise HTTPException(status_code=response.status_code, detail=f"Erro ao excluir ramal: {response.text}")
