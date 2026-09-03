"""
Serviço de diagnóstico de telefonia e ramal do usuário no Genesys Cloud.

Avalia se o usuário possui estação efetiva atribuída, se a estação está ASSOCIATED,
e se o telefone base correspondente está ativo com Site configurado.
Distingue Cenário 1 (Backend Íntegro / Falha Local) de Cenário 2 (Inconsistência Genesys).
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional
import httpx
from fastapi import HTTPException
from config import BASE_URL


async def get_user_telephony_diagnosis(
    user_id: str,
    client: httpx.AsyncClient,
    headers: dict[str, str],
) -> dict[str, Any]:
    """
    Diagnóstica o estado da telefonia do usuário no Genesys Cloud.
    """
    clean_id = user_id.strip("{}")

    # 1. Busca dados gerais do usuário com estação e telefonia
    user_url = f"{BASE_URL}/users/{clean_id}?expand=station,telephony"
    user_res = await client.get(user_url, headers=headers)

    if user_res.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail=f"Usuário '{clean_id}' não encontrado no Genesys Cloud.",
        )
    if user_res.status_code >= 400:
        raise HTTPException(
            status_code=user_res.status_code,
            detail=f"Erro ao consultar usuário na Genesys Cloud: {user_res.text}",
        )

    user_data = user_res.json()
    user_name = user_data.get("name")
    user_email = user_data.get("email") or user_data.get("username")

    station_info = user_data.get("station", {})
    effective_station = station_info.get("effectiveStation")

    station_id: Optional[str] = None
    station_name: Optional[str] = None
    station_status: Optional[str] = None
    station_type: Optional[str] = None
    line_appearance_id: Optional[str] = None

    phone_found: Optional[dict[str, Any]] = None

    # 2. Se possuir estação efetiva, busca detalhes da estação e telefone por lines.id em paralelo
    if effective_station:
        station_id = effective_station.get("id")
        station_name = (
            effective_station.get("providerInfo", {}).get("name")
            or effective_station.get("name")
        )

        station_req = client.get(f"{BASE_URL}/stations/{station_id}", headers=headers)
        phone_req = client.get(
            f"{BASE_URL}/telephony/providers/edges/phones?lines.id={station_id}",
            headers=headers,
        )

        st_res, phone_res = await asyncio.gather(station_req, phone_req, return_exceptions=True)

        if isinstance(st_res, httpx.Response) and st_res.status_code == 200:
            st_data = st_res.json()
            station_status = st_data.get("status")
            station_type = st_data.get("type")
            line_appearance_id = st_data.get("lineAppearanceId")
            if st_data.get("name"):
                station_name = st_data.get("name")
        elif isinstance(st_res, httpx.Response):
            station_status = None

        if isinstance(phone_res, httpx.Response) and phone_res.status_code == 200:
            entities = phone_res.json().get("entities", [])
            if entities:
                phone_found = entities[0]

    # 3. Se não encontrou telefone por lines.id, faz fallback para webRtcUser.id
    if not phone_found:
        try:
            fallback_res = await client.get(
                f"{BASE_URL}/telephony/providers/edges/phones?webRtcUser.id={clean_id}",
                headers=headers,
            )
            if fallback_res.status_code == 200:
                entities = fallback_res.json().get("entities", [])
                if entities:
                    phone_found = entities[0]
        except Exception:
            pass

    # 4. Dados do telefone
    phone_id = phone_found.get("id") if phone_found else None
    phone_name = phone_found.get("name") if phone_found else None
    phone_state = phone_found.get("state") if phone_found else None
    site_info = phone_found.get("site") if phone_found else None
    phone_base_settings = phone_found.get("phoneBaseSettings") if phone_found else None

    # 5. Avaliação dos 3 pilares
    is_station_ok = bool(effective_station)
    is_conn_ok = station_status == "ASSOCIATED"
    is_phone_ok = bool(
        phone_found
        and phone_state == "active"
        and site_info
        and site_info.get("id")
    )

    is_healthy = bool(is_station_ok and is_conn_ok and is_phone_ok)

    issues: list[str] = []
    if not is_station_ok:
        issues.append("Usuário não possui estação efetiva atribuída no Genesys Cloud.")
    elif not is_conn_ok:
        issues.append(
            f"Estação não está associada com a central (Status atual: {station_status or 'Desconhecido/Desconectado'})."
        )

    if not phone_found:
        issues.append("Nenhum telefone base configurado para a linha/usuário.")
    else:
        if phone_state != "active":
            issues.append(f"Telefone base está com estado inativo ('{phone_state}').")
        if not site_info or not site_info.get("id"):
            issues.append("Telefone base não possui Site vinculado (rotas e chamadas externas falharão).")

    if is_healthy:
        scenario = 1
        scenario_title = "Cenário 1: Backend Íntegro (Problema Local na Máquina)"
        diagnosis = (
            "A configuração de telefonia no Genesys Cloud está 100% correta e operacional. "
            "A estação está associada e o telefone base está ativo com Site configurado. "
            "Se o usuário relatar chamadas caindo ou falha de áudio, a causa raiz está na "
            "estação de trabalho local do usuário (cache, concorrência de abas ou microfone)."
        )
        recommendations = [
            "Garantir que todas as outras abas ou janelas do Genesys Cloud estejam fechadas.",
            "Limpar cache e cookies de todo o período no navegador e reiniciar a sessão.",
            "Verificar permissões de microfone nas configurações do navegador e do sistema operacional.",
            "Executar o teste em Configurações > Diagnósticos WebRTC no Genesys Cloud.",
        ]
    else:
        scenario = 2
        scenario_title = "Cenário 2: Inconsistência na Configuração do Genesys Cloud"
        diagnosis = (
            "Foi detectada inconsistência na configuração de telefonia do usuário no Genesys Cloud. "
            "A equipe de TI/Suporte precisa ajustar a configuração no painel administrativo antes "
            "de solicitar testes na máquina do usuário."
        )
        recommendations = [
            "Acessar Admin > Telefonia > Telefones no Genesys Cloud.",
            "Verificar a associação do ramal e garantir que a estação esteja atribuída ao usuário.",
            "Confirmar se o telefone base está Ativo e associado a um Site válido com plano de discagem.",
            "Após ajustar no Admin, solicitar que o colaborador efetue logout e novo login.",
        ]

    return {
        "user_id": clean_id,
        "user_name": user_name,
        "user_email": user_email,
        "scenario": scenario,
        "scenario_title": scenario_title,
        "is_healthy": is_healthy,
        "diagnosis": diagnosis,
        "recommendations": recommendations,
        "issues": issues,
        "station": (
            {
                "id": station_id,
                "name": station_name,
                "status": station_status,
                "type": station_type,
                "line_appearance_id": line_appearance_id,
                "is_associated": (station_status == "ASSOCIATED"),
            }
            if effective_station
            else None
        ),
        "phone": (
            {
                "id": phone_id,
                "name": phone_name,
                "state": phone_state,
                "site": (
                    {
                        "id": site_info.get("id"),
                        "name": site_info.get("name") or site_info.get("id"),
                    }
                    if site_info
                    else None
                ),
                "phone_base_settings": (
                    {
                        "id": phone_base_settings.get("id"),
                        "name": phone_base_settings.get("name")
                        or phone_base_settings.get("id"),
                    }
                    if phone_base_settings
                    else None
                ),
            }
            if phone_found
            else None
        ),
        "summary": {
            "station_assigned": is_station_ok,
            "station_associated": is_conn_ok,
            "phone_active": is_phone_ok,
        },
    }
