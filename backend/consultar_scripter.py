import asyncio
import json
import os
import sys
import httpx
from auth import get_token, h
from config import BASE_URL

EXACT_SCRIPTS = [
    "Atendimento_Voz_Bolsa_Familia",
    "Atendimento_Voz_Bolsa_Familia_Callback",
    "Atendimento_Voz_Comercial",
    "Atendimento_Voz_Comercial_Callback",
    "Atendimento_Voz_Habitacao",
    "Atendimento_Voz_Habitacao_Callback",
    "Atendimento_Voz_Cartão",
    "Atendimento_Voz_Cartão_Callback",
    "Atendimento_Voz_Parceiros",
    "Atendimento_Voz_Parceiros_Callback",
    "Atendimento_Voz_cidadao",
    "Atendimento_Voz_cidadao_callBack",
    "Atendimento_Voz_Demais_SEG",
    "Atendimento_Voz_Demais_SEG_Callback"
]

async def get_script_by_name(client: httpx.AsyncClient, headers: dict, name: str) -> str:
    url = f"{BASE_URL}/scripts?name={name}"
    resp = await client.get(url, headers=headers)
    if resp.status_code == 200:
        entities = resp.json().get('entities', [])
        for entity in entities:
            if entity.get('name').lower() == name.lower():
                return entity.get('id')
    return None

async def get_script_pages(client: httpx.AsyncClient, headers: dict, script_id: str) -> list:
    url = f"{BASE_URL}/scripts/published/{script_id}/pages"
    resp = await client.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return []

async def get_page_content(client: httpx.AsyncClient, headers: dict, script_id: str, page_id: str) -> dict:
    url = f"{BASE_URL}/scripts/published/{script_id}/pages/{page_id}"
    resp = await client.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return {}

def search_callback_elements(node, path=''):
    results = []
    if isinstance(node, dict):
        # Identify if this node is an interesting element
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

async def main():
    print("Obtendo token de autenticação Genesys Cloud...")
    token = await get_token()
    headers = h(token)
    
    results = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for name in EXACT_SCRIPTS:
            print(f"\nProcurando script: {name}")
            
            script_id = await get_script_by_name(client, headers, name)
            if not script_id:
                print(f"  -> Script '{name}' não encontrado.")
                continue
                
            print(f"  -> ID: {script_id}")
            pages = await get_script_pages(client, headers, script_id)
            
            script_data = {
                "id": script_id,
                "pages": {}
            }
            
            for page in pages:
                page_id = page.get('id')
                page_name = page.get('name')
                print(f"  -> Inspecionando página: {page_name} ({page_id})")
                
                content = await get_page_content(client, headers, script_id, page_id)
                callback_elements = search_callback_elements(content)
                
                script_data["pages"][page_id] = {
                    "name": page_name,
                    "callback_elements": callback_elements,
                    "raw": content
                }
                
                # Print found elements immediately
                for el in callback_elements:
                    # only print elements that look like actual components (buttons, panels, containers)
                    props = el['properties']
                    if 'visible' in props or 'text' in props or el['type'] in ['button', 'container', 'text']:
                        visible_prop = props.get('visible')
                        text_prop = props.get('text')
                        print(f"     [Elemento] Nome: {el['name']} | Tipo: {el['type']}")
                        if text_prop:
                            print(f"       Texto: {text_prop}")
                        if visible_prop:
                            print(f"       Visible: {visible_prop}")
                            
            results[name] = script_data

    with open("retorno_scripter.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\nExtração completa salva em retorno_scripter.json")

if __name__ == "__main__":
    asyncio.run(main())
