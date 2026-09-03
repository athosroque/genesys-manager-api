import asyncio
import httpx
import json
import sys
from auth import get_token, h
from config import BASE_URL

async def validate_user_telephony(user_id: str):
    print(f"Obtendo token para consultar Genesys Cloud...")
    try:
        token = await get_token()
    except Exception as e:
        print(f"Erro ao obter token: {e}")
        return

    headers = h(token)
    
    async with httpx.AsyncClient() as client:
        # 1. Usuário Geral e Estação Efetiva
        print(f"\n{'='*60}")
        print("1. Consultando Usuário e Estação Efetiva")
        print(f"GET {BASE_URL}/users/{user_id}?expand=station,telephony,presence")
        print(f"{'='*60}")
        
        user_res = await client.get(f"{BASE_URL}/users/{user_id}?expand=station,telephony,presence", headers=headers)
        if user_res.status_code != 200:
            print(f"Erro ({user_res.status_code}): {user_res.text}")
            return
            
        user_data = user_res.json()
        print(f"Nome: {user_data.get('name')}")
        print(f"Email/Username: {user_data.get('username')}")
        print(f"Presença: {user_data.get('presence', {}).get('presenceDefinition', {}).get('systemPresence')}")
        
        station_info = user_data.get("station", {})
        effective_station = station_info.get("effectiveStation")
        print(f"Estação Efetiva Presente? {'SIM' if effective_station else 'NÃO'}")
        
        station_id = effective_station.get("id") if effective_station else None
        if station_id:
            print(f"Station ID: {station_id}")
            print(f"Nome da Linha/Estação: {effective_station.get('providerInfo', {}).get('name')}")

        # 2. Status Detalhado da Estação
        print(f"\n{'='*60}")
        print("2. Consultando Status Detalhado da Estação")
        print(f"GET {BASE_URL}/users/{user_id}/station")
        print(f"{'='*60}")
        
        user_station_res = await client.get(f"{BASE_URL}/users/{user_id}/station", headers=headers)
        print(f"Status Code (/users/{{userId}}/station): {user_station_res.status_code}")
        if user_station_res.status_code == 200:
            print(json.dumps(user_station_res.json(), indent=2, ensure_ascii=False))
        else:
            print(f"Resposta: {user_station_res.text}")

        station_status = None
        if station_id:
            st_res = await client.get(f"{BASE_URL}/stations/{station_id}", headers=headers)
            if st_res.status_code == 200:
                st_data = st_res.json()
                station_status = st_data.get("status")
                print(f"Status da Estação: {station_status}")
                print(f"Tipo da Estação: {st_data.get('type')}")
                print(f"Line Appearance: {st_data.get('lineAppearanceId')}")
            else:
                print(f"Erro ao consultar estação por ID ({st_res.status_code}): {st_res.text}")
        else:
            print("Usuário não possui estação efetiva associada no momento.")

        # 3. Configuração do Telefone Base (Phone)
        print(f"\n{'='*60}")
        print("3. Consultando Telefone Base (Edge Phone)")
        print(f"{'='*60}")
        
        phone_found = None
        # Tenta buscar por lines.id (estação)
        if station_id:
            phone_res = await client.get(f"{BASE_URL}/telephony/providers/edges/phones?lines.id={station_id}", headers=headers)
            if phone_res.status_code == 200:
                entities = phone_res.json().get("entities", [])
                if entities:
                    phone_found = entities[0]
                    print("Telefone encontrado via Linha/Estação (lines.id):")
            else:
                print(f"Aviso na busca por lines.id ({phone_res.status_code}): {phone_res.text}")

        # Tenta buscar por webRtcUser.id se não achou
        if not phone_found:
            phone_res = await client.get(f"{BASE_URL}/telephony/providers/edges/phones?webRtcUser.id={user_id}", headers=headers)
            if phone_res.status_code == 200:
                entities = phone_res.json().get("entities", [])
                if entities:
                    phone_found = entities[0]
                    print("Telefone encontrado via webRtcUser.id:")

        if phone_found:
            print(f"ID do Telefone: {phone_found.get('id')}")
            print(f"Nome: {phone_found.get('name')}")
            print(f"Estado (State): {phone_found.get('state')}")
            print(f"Site ID: {phone_found.get('site', {}).get('id')}")
            print(f"Phone Base Settings ID: {phone_found.get('phoneBaseSettings', {}).get('id')}")
        else:
            print("Nenhum telefone base retornado para este usuário/linha.")

        # Resumo / Diagnóstico
        print(f"\n{'='*60}")
        print("📊 RESUMO DO DIAGNÓSTICO (BACKEND GENESYS)")
        print(f"{'='*60}")
        is_station_ok = bool(effective_station)
        is_conn_ok = (station_status == "ASSOCIATED")
        is_phone_ok = bool(phone_found and phone_found.get("state") == "active" and phone_found.get("site"))

        print(f"1. Estação Atribuída: {'🟢 OK' if is_station_ok else '🔴 FALHA (Sem estação)'}")
        print(f"2. Conexão da Estação: {'🟢 ASSOCIATED' if is_conn_ok else f'🔴 {station_status or 'DESCONECTADO'}'}")
        print(f"3. Telefone Base: {'🟢 ATIVO COM SITE' if is_phone_ok else '🔴 INCONSISTENTE/INEXISTENTE'}")

        if is_station_ok and is_conn_ok and is_phone_ok:
            print("\n👉 RESULTADO: CENÁRIO 1 (Backend 100% correto). Problema isolado na máquina do usuário (cache/concorrência).")
        else:
            print("\n👉 RESULTADO: CENÁRIO 2 (Inconsistência no Genesys Cloud encontrada). Ajustar configuração no Admin.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python validate_webrtc.py <user_id>")
        sys.exit(1)
        
    user_id = sys.argv[1]
    asyncio.run(validate_user_telephony(user_id))
