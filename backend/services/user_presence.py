"""
Presença (primaryPresence) via Genesys Analytics User Status Detail.

Calcula o intervalo do dia civil em America/Sao_Paulo e normaliza a resposta
de POST /api/v2/analytics/users/details/query para o contrato interno da
Consulta e Ações.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

TZ_BR = ZoneInfo("America/Sao_Paulo")
KNOWN_PRESENCES = ("AVAILABLE", "OFFLINE", "BUSY", "AWAY", "BREAK")
# Limite histórico aproximado do endpoint síncrono de user details (Genesys).
MAX_HISTORY_DAYS = 558


def today_br(now: Optional[datetime] = None) -> date:
    """Data civil de hoje em America/Sao_Paulo."""
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(TZ_BR).date()


def interval_for_br_date(day: date) -> str:
    """
    Dia civil BR → intervalo ISO-8601 UTC com sufixo Z.

    Ex.: 2026-08-05 → 2026-08-05T03:00:00Z/2026-08-06T03:00:00Z (−03).
    Usa zoneinfo/IANA — sem offset fixo hardcoded.
    """
    local_start = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=TZ_BR)
    local_end = local_start + timedelta(days=1)
    start_utc = local_start.astimezone(timezone.utc)
    end_utc = local_end.astimezone(timezone.utc)
    return f"{_fmt_z(start_utc)}/{_fmt_z(end_utc)}"


def validate_presence_date(day: date, *, now: Optional[datetime] = None) -> None:
    """
    Valida a data de consulta. Levanta ValueError com mensagem em PT-BR.

    - Futura → inválida
    - Mais antiga que MAX_HISTORY_DAYS → inválida
    """
    today = today_br(now)
    if day > today:
        raise ValueError(
            f"Data futura não permitida. Informe um dia até {today.isoformat()} "
            "(fuso America/Sao_Paulo)."
        )
    oldest = today - timedelta(days=MAX_HISTORY_DAYS)
    if day < oldest:
        raise ValueError(
            f"Data fora do histórico suportado (~{MAX_HISTORY_DAYS} dias). "
            f"Use uma data a partir de {oldest.isoformat()}."
        )


def parse_iso_utc(value: str) -> datetime:
    """Parse ISO-8601 com Z ou offset → datetime aware UTC."""
    text = (value or "").strip()
    if not text:
        raise ValueError("timestamp vazio")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    """Início inclusivo e fim exclusivo do dia civil BR, em UTC."""
    local_start = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=TZ_BR)
    local_end = local_start + timedelta(days=1)
    return local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)


def parse_primary_presence(
    payload: dict[str, Any],
    *,
    now: Optional[datetime] = None,
    day: Optional[date] = None,
) -> dict[str, Any]:
    """
    Extrai segmentos de primaryPresence e totais em minutos.

    endTime ausente → usa `now` (UTC) e marca is_open / open_segment.
    Se `day` for informado, recorta cada segmento ao intervalo do dia civil BR
    (evita durações >24h e horários 10:59–10:00 por atravessar meia-noite).
    """
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    else:
        instant = instant.astimezone(timezone.utc)

    day_start_utc: Optional[datetime] = None
    day_end_utc: Optional[datetime] = None
    if day is not None:
        day_start_utc, day_end_utc = day_bounds_utc(day)

    user_details = payload.get("userDetails") or []
    raw_segments: list[dict] = []
    for detail in user_details:
        for item in detail.get("primaryPresence") or []:
            raw_segments.append(item)

    segments: list[dict[str, Any]] = []
    open_segment = False

    for item in raw_segments:
        start_raw = item.get("startTime")
        if not start_raw:
            continue
        try:
            start_utc = parse_iso_utc(start_raw)
        except ValueError:
            continue

        end_raw = item.get("endTime")
        raw_open = not end_raw
        if raw_open:
            end_utc = instant
        else:
            try:
                end_utc = parse_iso_utc(end_raw)
            except ValueError:
                continue

        if end_utc < start_utc:
            continue

        is_open = raw_open
        if day_start_utc is not None and day_end_utc is not None:
            # Sem overlap com o dia consultado → ignora
            if end_utc <= day_start_utc or start_utc >= day_end_utc:
                continue
            if start_utc < day_start_utc:
                start_utc = day_start_utc
            if end_utc > day_end_utc:
                end_utc = day_end_utc
            # Segmento aberto só no dia civil de "agora"; dias passados fecham às 24:00
            if raw_open and today_br(instant) == day:
                is_open = True
                end_utc = min(instant, day_end_utc)
            else:
                is_open = False

        if end_utc <= start_utc:
            continue

        if is_open:
            open_segment = True

        duration_minutes = round((end_utc - start_utc).total_seconds() / 60.0, 2)
        # Guarda-rail: um dia civil não deve reportar > 24h por segmento
        if duration_minutes > 24 * 60:
            duration_minutes = float(24 * 60)

        system_presence = (item.get("systemPresence") or "UNKNOWN").strip() or "UNKNOWN"
        org_id = item.get("organizationPresenceId")

        segments.append(
            {
                "system_presence": system_presence,
                "start": _fmt_offset(start_utc.astimezone(TZ_BR)),
                "end": _fmt_offset(end_utc.astimezone(TZ_BR)),
                "start_utc": _fmt_z_ms(start_utc),
                "end_utc": _fmt_z_ms(end_utc),
                "duration_minutes": duration_minutes,
                "organization_presence_id": org_id,
                "is_open": is_open,
            }
        )

    segments.sort(key=lambda s: s["start_utc"])

    totals: dict[str, float] = {k: 0.0 for k in KNOWN_PRESENCES}
    for seg in segments:
        key = seg["system_presence"]
        totals[key] = round(totals.get(key, 0.0) + seg["duration_minutes"], 2)

    # Remove zeros de status desconhecidos para não poluir; mantém known mesmo em 0.
    cleaned: dict[str, float] = {}
    for key, value in totals.items():
        if key in KNOWN_PRESENCES or value:
            cleaned[key] = value

    total_tracked = round(sum(cleaned.values()), 2)
    empty = len(segments) == 0

    return {
        "segments": segments,
        "totals_minutes": cleaned if not empty else {},
        "total_tracked_minutes": total_tracked if not empty else 0.0,
        "open_segment": open_segment,
        "empty": empty,
    }


def build_presence_response(
    *,
    user_id: str,
    day: date,
    payload: dict[str, Any],
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Monta o contrato interno completo da rota de presença."""
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    parsed = parse_primary_presence(payload, now=instant, day=day)
    return {
        "user_id": user_id,
        "date": day.isoformat(),
        "timezone": "America/Sao_Paulo",
        "interval": interval_for_br_date(day),
        "queried_at": _fmt_z(instant.astimezone(timezone.utc)),
        "open_segment": parsed["open_segment"],
        "segments": parsed["segments"],
        "totals_minutes": parsed["totals_minutes"],
        "total_tracked_minutes": parsed["total_tracked_minutes"],
        "empty": parsed["empty"],
    }


def _fmt_z(dt: datetime) -> str:
    """UTC sem microssegundos, sufixo Z."""
    utc = dt.astimezone(timezone.utc).replace(microsecond=0)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_z_ms(dt: datetime) -> str:
    """UTC com milissegundos quando houver, sufixo Z."""
    utc = dt.astimezone(timezone.utc)
    ms = utc.microsecond // 1000
    if ms:
        return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_offset(dt: datetime) -> str:
    """ISO com offset numérico (ex. -03:00) para exibição BR."""
    return dt.isoformat(timespec="seconds")
