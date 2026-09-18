import asyncio
import re
from fastapi import APIRouter, Depends, Path, HTTPException, Query
from typing import Dict, Any

from auth import get_token, h
from auth_local import get_current_user
from config import BASE_URL
import httpx

router = APIRouter()

UUID_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

MAX_RETRIES = 5
DEFAULT_RETRY_SECONDS = 2.0
HTTP_TIMEOUT = 30.0

def _retry_after_seconds(resp: httpx.Response) -> float:
    header = resp.headers.get("Retry-After")
    if header:
        try:
            return max(float(header), 0.5)
        except ValueError:
            pass
    try:
        message = resp.json().get("message", "")
        match = re.search(r"\[(\d+(?:\.\d+)?)\]", message)
        if match:
            return max(float(match.group(1)), 0.5)
    except Exception:
        pass
    return DEFAULT_RETRY_SECONDS


async def genesys_request(
    method: str,
    path: str,
    *,
    json_data: dict | None = None,
    params: dict | None = None,
) -> Any:
    token = await get_token()
    headers = h(token)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        for attempt in range(MAX_RETRIES + 1):
            resp = await client.request(
                method, f"{BASE_URL}{path}", json=json_data, params=params, headers=headers
            )
            if resp.status_code != 429 or attempt == MAX_RETRIES:
                break
            await asyncio.sleep(_retry_after_seconds(resp))

    if resp.status_code == 404:
        return None
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, f"Genesys API Error: {resp.text[:300]}")
    return resp.json() if resp.text else {}


@router.get("/{conversation_id}")
async def get_diagnostic_data(
    conversation_id: str = Path(..., description="UUID Genesys da conversa"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Busca os detalhes de analytics e do call state de uma conversa no Genesys Cloud
    para alimentar o Dashboard de Diagnóstico.
    """
    uid = conversation_id.strip("{}")
    if not UUID_REGEX.match(uid):
        raise HTTPException(422, "conversation_id deve ser um UUID válido.")

    # Disparar chamadas em paralelo para /analytics/conversations/{id}/details 
    # e para /conversations/{id}
    details_task = genesys_request("GET", f"/analytics/conversations/{uid}/details")
    calls_task = genesys_request("GET", f"/conversations/{uid}")

    results = await asyncio.gather(details_task, calls_task, return_exceptions=True)
    
    details_data = results[0]
    calls_data = results[1]

    if isinstance(details_data, Exception):
        raise HTTPException(500, f"Erro buscando details: {str(details_data)}")
    if isinstance(calls_data, Exception):
        raise HTTPException(500, f"Erro buscando calls: {str(calls_data)}")

    if not details_data:
        raise HTTPException(404, "Conversa não encontrada nos registros de analytics.")

    return {
        "details": details_data,
        "calls": calls_data or {}
    }


@router.get("/{conversation_id}/advanced-audit")
async def get_advanced_audit(
    conversation_id: str = Path(..., description="UUID Genesys da conversa"),
    queue_id: str = Query(None, description="Sobrescreve a fila automática"),
    user_id: str = Query(None, description="Sobrescreve o usuário automático"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Busca detalhes do analytics da conversa e cruza com dados de fila, wrapup, assistant e apps
    para gerar um JSON de auditoria avançada.
    """
    uid = conversation_id.strip("{}")
    if not UUID_REGEX.match(uid):
        raise HTTPException(422, "conversation_id deve ser um UUID válido.")

    details = await genesys_request("GET", f"/analytics/conversations/{uid}/details")
    if not details:
        raise HTTPException(404, "Conversa não encontrada nos registros de analytics.")

    found_queue_ids = []
    found_user_ids = []

    participants = details.get("participants", [])
    for p in participants:
        purpose = p.get("purpose")
        
        if purpose in ("agent", "user"):
            u = p.get("userId")
            if u and u not in found_user_ids:
                found_user_ids.append(u)
                
        sessions = p.get("sessions", [])
        for s in sessions:
            segments = s.get("segments", [])
            for seg in segments:
                q = seg.get("queueId")
                if q and q not in found_queue_ids:
                    found_queue_ids.append(q)

    used_queue_id = queue_id or (found_queue_ids[0] if found_queue_ids else None)
    used_user_id = user_id or (found_user_ids[0] if found_user_ids else None)

    tasks = {}
    
    if used_queue_id:
        tasks["queue"] = genesys_request("GET", f"/routing/queues/{used_queue_id}")
        tasks["wrapupcodes"] = genesys_request("GET", f"/routing/queues/{used_queue_id}/wrapupcodes")
        tasks["assistant"] = genesys_request("GET", f"/routing/queues/{used_queue_id}/assistant")
        
    if used_user_id:
        tasks["subject_roles"] = genesys_request("GET", f"/authorization/subjects/{used_user_id}")
        
    tasks["clientapps"] = genesys_request("GET", "/integrations/unifiedcommunications/clientapps")
    
    results = {}
    if tasks:
        keys = list(tasks.keys())
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for k, res in zip(keys, gathered):
            if isinstance(res, Exception):
                results[k] = {"error": str(res)}
            else:
                results[k] = res

    return {
        "found_queue_ids": found_queue_ids,
        "found_user_ids": found_user_ids,
        "used_queue_id": used_queue_id,
        "used_user_id": used_user_id,
        "audit_data": results
    }

