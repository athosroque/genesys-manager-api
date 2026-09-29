import json
import httpx
import re
from fastapi import HTTPException
from auth import get_token, h
from config import BASE_URL

async def get_flow_id_by_name(client: httpx.AsyncClient, headers: dict, name: str) -> str:
    url = f"{BASE_URL}/flows?name={name}"
    resp = await client.get(url, headers=headers)
    if resp.status_code == 200:
        entities = resp.json().get('entities', [])
        for entity in entities:
            if entity.get('name', '').lower() == name.lower():
                return entity.get('id')
    return None

def extract_flow_summary(flow_config: dict) -> dict:
    """
    Filtra o JSON gigante do fluxo (1MB+) para um sumário legível das tarefas e decisões.
    """
    summary = {
        "flowId": flow_config.get("id"),
        "name": flow_config.get("name"),
        "type": flow_config.get("type"),
        "tasks": []
    }
    
    tasks = flow_config.get("manifest", {}).get("tasks", {})
    if not tasks:
        # Tenta outra estrutura comum dependendo do tipo do fluxo
        return summary
        
    for task_key, task_val in tasks.items():
        task_info = {
            "name": task_val.get("name"),
            "actions": []
        }
        
        # Iterar sobre actions e pegar as importantes
        actions = task_val.get("actions", [])
        for action in actions:
            action_type = action.get("type")
            action_name = action.get("name")
            
            # Filtra apenas ações de interesse (Switch, DataTable, SetParticipantData, Transfer)
            if action_type in ["DataTableLookupAction", "SwitchAction", "SetParticipantDataAction", "TransferToQueueAction"]:
                action_info = {
                    "type": action_type,
                    "name": action_name,
                    "details": {}
                }
                
                if action_type == "DataTableLookupAction":
                    action_info["details"]["dataTable"] = action.get("dataTable")
                    action_info["details"]["outputs"] = [
                        {"name": out.get("name"), "variable": out.get("variable")}
                        for out in action.get("outputs", [])
                    ]
                elif action_type == "SwitchAction":
                    action_info["details"]["evaluation"] = action.get("evaluation")
                    action_info["details"]["cases"] = [
                        {"value": case.get("value"), "destination": case.get("destination")}
                        for case in action.get("cases", [])
                    ]
                elif action_type == "SetParticipantDataAction":
                    action_info["details"]["attributes"] = action.get("attributes", [])
                elif action_type == "TransferToQueueAction":
                    action_info["details"]["queue"] = action.get("queue")
                    
                task_info["actions"].append(action_info)
                
        summary["tasks"].append(task_info)
        
    return summary

async def get_flow_diagnostics(name_or_id: str) -> dict:
    token = await get_token()
    headers = h(token)
    
    is_uuid = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', name_or_id.lower())
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        if is_uuid:
            flow_id = name_or_id
        else:
            flow_id = await get_flow_id_by_name(client, headers, name_or_id)
            if not flow_id:
                raise HTTPException(status_code=404, detail=f"Fluxo com nome '{name_or_id}' não encontrado.")
                
        url = f"{BASE_URL}/flows/{flow_id}/latestconfiguration"
        resp = await client.get(url, headers=headers)
        
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"Falha ao buscar fluxo {flow_id}.")
            
        raw_config = resp.json()
        summary = extract_flow_summary(raw_config)
        
        return {
            "raw": raw_config,
            "summary": summary
        }

async def get_script_by_name(client: httpx.AsyncClient, headers: dict, name: str) -> str:
    url = f"{BASE_URL}/scripts?name={name}"
    resp = await client.get(url, headers=headers)
    if resp.status_code == 200:
        entities = resp.json().get('entities', [])
        for entity in entities:
            if entity.get('name', '').lower() == name.lower():
                return entity.get('id')
    return None

def search_callback_elements(node, path=''):
    results = []
    if isinstance(node, dict):
        is_callback = False
        node_str = json.dumps(node, ensure_ascii=False).lower()
        if 'callback' in node_str or 'retorno' in node_str:
            is_callback = True
            
        if is_callback and ('type' in node or 'visible' in node.get('properties', {})):
            results.append({
                'path': path,
                'name': node.get('name', 'N/A'),
                'type': node.get('type', 'N/A'),
                'properties': node.get('properties', {})
            })
            
        for k, v in node.items():
            results.extend(search_callback_elements(v, path + f".{k}" if path else k))
    elif isinstance(node, list):
        for i, item in enumerate(node):
            results.extend(search_callback_elements(item, f"{path}[{i}]"))
    return results

async def get_script_diagnostics(name_or_id: str) -> dict:
    token = await get_token()
    headers = h(token)
    
    is_uuid = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', name_or_id.lower())
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        if is_uuid:
            script_id = name_or_id
            script_name = name_or_id # we might not have the name immediately, but we can fetch it if needed later
        else:
            script_id = await get_script_by_name(client, headers, name_or_id)
            script_name = name_or_id
            if not script_id:
                raise HTTPException(status_code=404, detail=f"Script '{name_or_id}' não encontrado.")
            
        pages_url = f"{BASE_URL}/scripts/published/{script_id}/pages"
        pages_resp = await client.get(pages_url, headers=headers)
        if pages_resp.status_code != 200:
            raise HTTPException(status_code=pages_resp.status_code, detail="Falha ao buscar páginas do script.")
            
        pages = pages_resp.json()
        
        script_data = {
            "id": script_id,
            "name": script_name,
            "pages": {}
        }
        
        summary = []
        
        for page in pages:
            page_id = page.get('id')
            page_name = page.get('name')
            
            content_url = f"{BASE_URL}/scripts/published/{script_id}/pages/{page_id}"
            content_resp = await client.get(content_url, headers=headers)
            content = content_resp.json() if content_resp.status_code == 200 else {}
            
            callback_elements = search_callback_elements(content)
            
            script_data["pages"][page_id] = {
                "name": page_name,
                "callback_elements": callback_elements,
                "raw": content
            }
            
            if callback_elements:
                page_summary = {
                    "page_id": page_id,
                    "page_name": page_name,
                    "elements": []
                }
                for el in callback_elements:
                    props = el['properties']
                    if 'visible' in props or 'text' in props or el['type'] in ['button', 'container', 'text']:
                        page_summary["elements"].append({
                            "name": el.get('name'),
                            "type": el.get('type'),
                            "visible": props.get('visible'),
                            "text": props.get('text')
                        })
                if page_summary["elements"]:
                    summary.append(page_summary)
                    
        return {
            "raw": script_data,
            "summary": summary
        }
