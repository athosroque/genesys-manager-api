from fastapi import APIRouter, HTTPException, Query
from services.genesys_system import get_flow_diagnostics, get_script_diagnostics

router = APIRouter()

@router.get("/flow")
async def get_flow(name_or_id: str = Query(..., description="Nome exato ou ID do Fluxo")):
    """
    Busca as configurações do fluxo na Genesys Cloud (latestconfiguration),
    retornando um JSON processado (resumo de tarefas) e o JSON original completo.
    """
    try:
        data = await get_flow_diagnostics(name_or_id)
        return data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao buscar fluxo: {str(e)}")

@router.get("/script")
async def get_script(
    name: str = Query(None, description="Nome exato ou ID do Script"),
    name_or_id: str = Query(None, description="Nome exato ou ID do Script")
):
    """
    Busca um script publicado e suas páginas (por Nome ou ID/UUID), extraindo elementos de UI de callback.
    Retorna o JSON processado (elementos encontrados) e o JSON original completo.
    """
    query_val = name or name_or_id
    if not query_val:
        raise HTTPException(status_code=400, detail="Parâmetro 'name' ou 'name_or_id' é obrigatório.")
    try:
        data = await get_script_diagnostics(query_val)
        return data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao buscar script: {str(e)}")

