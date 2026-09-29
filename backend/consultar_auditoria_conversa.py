"""
Consulta de Auditoria e Rastreabilidade de Transferência de Conversa
Genesys Cloud Platform API

Este script realiza a consulta completa para determinar a autoria e os dados
de uma transferência de conversa:
1. Extração analítica detalhada da conversa (participantes, sessões, segmentos, disconnectType)
2. Extração via Conversation API (atributos do participante, ACW, wrapup, clientIpAddress)
3. Consulta à Genesys Platform Audit API (ContactCenter/ConversationAttributes e Supportability)
4. Mapeamento do Script associado e ações de transferência (Scripter API)
"""

import asyncio
import json
import os
import sys
import time
import httpx
from datetime import datetime
from dotenv import load_dotenv

from auth import get_token, h
from config import BASE_URL

CONVERSATION_ID = "6b343b6b-47bf-4bab-be76-15a7f7d74237"
START_INTERVAL = "2026-09-21T13:15:00.000Z"
END_INTERVAL = "2026-09-21T13:30:00.000Z"


async def get_analytics_conversation(client: httpx.AsyncClient, headers: dict, conv_id: str) -> dict:
    url = f"{BASE_URL}/analytics/conversations/{conv_id}/details"
    resp = await client.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return {"status_code": resp.status_code, "error": resp.text}


async def get_conversation_api(client: httpx.AsyncClient, headers: dict, conv_id: str) -> dict:
    url = f"{BASE_URL}/conversations/{conv_id}"
    resp = await client.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return {"status_code": resp.status_code, "error": resp.text}


async def query_platform_audits(client: httpx.AsyncClient, headers: dict, service_name: str, entity_type: str, entity_id: str) -> dict:
    payload = {
        "interval": f"{START_INTERVAL}/{END_INTERVAL}",
        "serviceName": service_name,
        "filters": [
            {"property": "EntityType", "value": entity_type},
            {"property": "EntityId", "value": entity_id}
        ]
    }
    create_url = f"{BASE_URL}/audits/query"
    resp = await client.post(create_url, headers=headers, json=payload)
    if resp.status_code not in (200, 202):
        return {"service": service_name, "status_code": resp.status_code, "error": resp.text}

    transaction_id = resp.json().get("id")
    for _ in range(15):
        await asyncio.sleep(2)
        status_resp = await client.get(f"{BASE_URL}/audits/query/{transaction_id}", headers=headers)
        state = status_resp.json().get("state")
        if state == "Succeeded":
            results_resp = await client.get(f"{BASE_URL}/audits/query/{transaction_id}/results", headers=headers)
            return {
                "service": service_name,
                "entityType": entity_type,
                "transactionId": transaction_id,
                "state": state,
                "entities": results_resp.json().get("entities", [])
            }
        elif state in ("Failed", "Cancelled"):
            return {
                "service": service_name,
                "entityType": entity_type,
                "transactionId": transaction_id,
                "state": state,
                "error": status_resp.text
            }

    return {"service": service_name, "transactionId": transaction_id, "state": "Timeout"}


async def get_script_details(client: httpx.AsyncClient, headers: dict, script_id: str) -> dict:
    url = f"{BASE_URL}/scripts/published/{script_id}"
    resp = await client.get(url, headers=headers)
    if resp.status_code == 200:
        script = resp.json()
        transfer_actions = []
        for a in script.get("customActions", []):
            if any(k in a.get("name", "").lower() for k in ["transfer", "tranfer"]):
                transfer_actions.append(a)
        return {
            "id": script_id,
            "name": script.get("name"),
            "transfer_actions": transfer_actions
        }
    return {"status_code": resp.status_code, "error": resp.text}


async def main():
    print(f"=== Auditoria de Conversa Genesys Cloud ===")
    print(f"Conversation ID: {CONVERSATION_ID}\n")

    token = await get_token()
    headers = h(token)

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("[1] Buscando detalhes analíticos da conversa...")
        analytics_data = await get_analytics_conversation(client, headers, CONVERSATION_ID)

        print("[2] Buscando atributos e dados em tempo real da conversa...")
        conv_api_data = await get_conversation_api(client, headers, CONVERSATION_ID)

        print("[3] Consultando Genesys Platform Audit API (ContactCenter/ConversationAttributes)...")
        audit_cc = await query_platform_audits(client, headers, "ContactCenter", "ConversationAttributes", CONVERSATION_ID)

        print("[4] Consultando Genesys Platform Audit API (Supportability/Conversation)...")
        audit_sup = await query_platform_audits(client, headers, "Supportability", "Conversation", CONVERSATION_ID)

        # Identificar script usado
        script_id = None
        for p in conv_api_data.get("participants", []):
            attrs = p.get("attributes", {})
            if "scriptId" in attrs:
                script_id = attrs["scriptId"]
                break

        script_info = None
        if script_id:
            print(f"[5] Analisando Script de Atendimento ({script_id})...")
            script_info = await get_script_details(client, headers, script_id)

        # Monta relatório consolidado
        report = {
            "conversationId": CONVERSATION_ID,
            "interval_audited": f"{START_INTERVAL} / {END_INTERVAL}",
            "audit_viewer_results": {
                "ContactCenter_ConversationAttributes": audit_cc,
                "Supportability_Conversation": audit_sup,
                "nota_tecnica": (
                    "O Admin > Audit Viewer da Genesys Cloud registra auditoria administrativa "
                    "(mudanças em usuários, filas, permissões, integrações). Eventos operacionais de telefonia "
                    "(Hold, Mute, Transfer) não geram registros de auditoria administrativa. A autoria técnica "
                    "é determinada pelo cruzamento dos atributos de sessão, script e ACW."
                )
            },
            "evidence_chain": {
                "scriptId": script_id,
                "scriptName": script_info.get("name") if script_info else None,
                "script_transfer_actions": script_info.get("transfer_actions") if script_info else [],
                "conversation_attributes": [
                    {
                        "participantId": p.get("id"),
                        "purpose": p.get("purpose"),
                        "name": p.get("name"),
                        "attributes": p.get("attributes")
                    }
                    for p in conv_api_data.get("participants", [])
                    if p.get("attributes")
                ],
                "transfer_agent": next(
                    (
                        {
                            "name": p.get("name"),
                            "userId": p.get("userId"),
                            "wrapup": p.get("calls", [{}])[0].get("wrapup") if p.get("calls") else None,
                            "afterCallWork": p.get("calls", [{}])[0].get("afterCallWork") if p.get("calls") else None,
                            "clientIpAddress": p.get("calls", [{}])[0].get("clientIpAddress") if p.get("calls") else None,
                        }
                        for p in conv_api_data.get("participants", [])
                        if p.get("purpose") == "agent" and any(
                            c.get("disconnectType") == "transfer" for c in p.get("calls", [])
                        )
                    ),
                    None
                )
            },
            "full_analytics": analytics_data,
            "full_conversation": conv_api_data
        }

        output_file = "retorno_auditoria_conversa.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Auditoria concluída! Relatório salvo em: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
