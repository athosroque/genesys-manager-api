"""
Rotas de Divisões — lookup de nome por UUID (Trilha de Auditoria)
===================================================================

  GET /divisions
      Lista o mapa completo {id, name} de todas as divisões da org, paginando
      GET {BASE_URL}/authorization/divisions. Assim como roles, uma org tem
      poucas dezenas de divisões — 1 (ou poucas) chamada(s) resolve todos os
      chips de divisionId da timeline de auditoria de uma vez.

Permissão necessária na OAuth Client Credentials: authorization > division >
view. Sem ela a Genesys devolve 403 — aqui devolvemos {divisions: [], warning}
para o frontend degradar graciosamente (chips ficam como UUID abreviado).
"""

import httpx
from fastapi import APIRouter, Depends

from auth import get_token, h
from auth_local import get_current_user
from config import BASE_URL

router = APIRouter()

PAGE_SIZE = 100
MAX_PAGES = 25  # ~2500 divisões: folga enorme; evita varredura sem fim


@router.get("")
async def list_divisions(current_user: dict = Depends(get_current_user)) -> dict:
    """Mapa {id, name} de todas as divisões da org (paginado)."""
    token = await get_token()
    headers = h(token)

    divisions: list[dict] = []
    truncated = False

    async with httpx.AsyncClient(timeout=30) as client:
        for page_number in range(1, MAX_PAGES + 1):
            url = f"{BASE_URL}/authorization/divisions?pageSize={PAGE_SIZE}&pageNumber={page_number}"
            response = await client.get(url, headers=headers)

            if response.status_code == 403:
                return {
                    "divisions": [],
                    "warning": "sem permissão authorization:division:view",
                }
            if response.status_code >= 400:
                return {
                    "divisions": divisions,
                    "warning": f"erro ao listar divisões Genesys: {response.text[:200]}",
                }

            data = response.json()
            entities = data.get("entities", [])
            divisions.extend(
                {"id": e.get("id"), "name": e.get("name")}
                for e in entities
                if e.get("id")
            )

            page_count = data.get("pageCount", 1)
            if not entities or page_number >= page_count:
                break
            if page_number == MAX_PAGES:
                truncated = True

    return {"divisions": divisions, "truncated": truncated}
