"""
Script para consulta da fila e extração do fluxo Architect via Genesys Cloud API.

Uso:
    cd backend
    .venv/bin/python consultar_fila_e_fluxo.py
"""

import asyncio
import json
import os
import sys
import httpx
from auth import get_token, h
from config import BASE_URL

QUEUE_ID = "f1aeac1b-b7fc-41ea-9348-16c8ac09c8c4"
FLOW_ID = "3e96a995-135e-4977-9429-e39e0e57927a"


async def get_queue_details(client: httpx.AsyncClient, headers: dict) -> dict:
    url = f"{BASE_URL}/routing/queues/{QUEUE_ID}"
    resp = await client.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return {
        "status_code": resp.status_code,
        "error": resp.text
    }


async def export_architect_flow(client: httpx.AsyncClient, headers: dict) -> dict:
    # 1. Tenta obter os metadados do fluxo
    flow_url = f"{BASE_URL}/flows/{FLOW_ID}"
    resp_flow = await client.get(flow_url, headers=headers)
    
    flow_meta = None
    if resp_flow.status_code == 200:
        flow_meta = resp_flow.json()
    else:
        flow_meta = {
            "status_code": resp_flow.status_code,
            "error": resp_flow.text
        }

    # 2. Tenta obter a configuração mais recente diretamente
    config_url = f"{BASE_URL}/flows/{FLOW_ID}/latestconfiguration"
    resp_config = await client.get(config_url, headers=headers)
    latest_config = None
    if resp_config.status_code == 200:
        latest_config = resp_config.json()
    else:
        latest_config = {
            "status_code": resp_config.status_code,
            "error": resp_config.text
        }

    # 3. Tenta iniciar um job de exportação do Architect
    job_url = f"{BASE_URL}/flows/export/jobs"
    resp_job = await client.post(job_url, headers=headers, json={"flowIds": [FLOW_ID]})
    export_job = None
    if resp_job.status_code in (200, 202):
        export_job = resp_job.json()
    else:
        export_job = {
            "status_code": resp_job.status_code,
            "error": resp_job.text
        }

    return {
        "flow_metadata": flow_meta,
        "latest_configuration": latest_config,
        "export_job": export_job
    }


async def main():
    print("Obtendo token de autenticação Genesys Cloud...")
    token = await get_token()
    headers = h(token)

    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"\n[1] Consultando Fila {QUEUE_ID}...")
        queue_data = await get_queue_details(client, headers)
        
        print(f"[2] Tentando extração do Fluxo Architect {FLOW_ID}...")
        flow_data = await export_architect_flow(client, headers)

        output = {
            "queue": queue_data,
            "architect_flow": flow_data
        }

        # Salva o resultado em arquivo JSON formatado
        output_file = "retorno_fila_e_fluxo.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\nConcluído! Dados salvos em: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
