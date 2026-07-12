"""
Rotas de Roles/Funções — lookup de nome por UUID (Trilha de Auditoria)
======================================================================

  GET /roles
      Lista o mapa completo {id, name} de todas as roles da org, paginando
      GET {BASE_URL}/authorization/roles. Uma org tem poucas dezenas de roles,
      então isso é 1 (ou poucas) chamada(s) e resolve todos os chips de role
      da timeline de auditoria de uma vez, sem lookup por UUID.

Permissão necessária na OAuth Client Credentials: authorization > role > view.
Sem ela a Genesys devolve 403 — aqui devolvemos {roles: [], warning: ...} para
o frontend degradar graciosamente (chips ficam como UUID abreviado).
"""

import httpx
from fastapi import APIRouter, Depends

from auth import get_token, h
from auth_local import get_current_user
from config import BASE_URL

router = APIRouter()

PAGE_SIZE = 100
MAX_PAGES = 25  # ~2500 roles: folga enorme; evita varredura sem fim


@router.get("")
async def list_roles(current_user: dict = Depends(get_current_user)) -> dict:
    """Mapa {id, name} de todas as roles da org (paginado)."""
    token = await get_token()
    headers = h(token)

    roles: list[dict] = []
    truncated = False

    async with httpx.AsyncClient(timeout=30) as client:
        for page_number in range(1, MAX_PAGES + 1):
            url = f"{BASE_URL}/authorization/roles?pageSize={PAGE_SIZE}&pageNumber={page_number}"
            response = await client.get(url, headers=headers)

            if response.status_code == 403:
                return {
                    "roles": [],
                    "warning": "sem permissão authorization:role:view",
                }
            if response.status_code >= 400:
                # Não quebra a timeline: devolve o que já coletou + aviso.
                return {
                    "roles": roles,
                    "warning": f"erro ao listar roles Genesys: {response.text[:200]}",
                }

            data = response.json()
            entities = data.get("entities", [])
            roles.extend(
                {"id": e.get("id"), "name": e.get("name")}
                for e in entities
                if e.get("id")
            )

            page_count = data.get("pageCount", 1)
            if not entities or page_number >= page_count:
                break
            if page_number == MAX_PAGES:
                truncated = True

    return {"roles": roles, "truncated": truncated}
