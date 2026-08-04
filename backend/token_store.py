"""
Armazenamento persistente de tokens de magic link (uso único, curta validade).

Os tokens brutos nunca são gravados — apenas o hash SHA-256.
Arquivo: auth_tokens.json (gitignored).
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from config import settings

TOKENS_FILE = os.path.join(os.path.dirname(__file__), "auth_tokens.json")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def hash_token(raw_token: str) -> str:
    """Retorna o hash SHA-256 hexadecimal do token bruto."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _load() -> list[dict]:
    if not os.path.exists(TOKENS_FILE):
        return []
    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("tokens", [])
    except (json.JSONDecodeError, OSError):
        return []


def _save(tokens: list[dict]) -> None:
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump({"tokens": tokens}, f, ensure_ascii=False, indent=2)


def cleanup_expired(tokens: Optional[list[dict]] = None) -> list[dict]:
    """Remove entradas expiradas (e já usadas há mais de 24h)."""
    if tokens is None:
        tokens = _load()
    now = _now()
    kept: list[dict] = []
    for entry in tokens:
        expires_at = _parse_dt(entry.get("expires_at"))
        used_at = _parse_dt(entry.get("used_at"))
        if expires_at and expires_at < now and not used_at:
            continue
        if used_at and used_at < now - timedelta(hours=24):
            continue
        kept.append(entry)
    return kept


def create_magic_link_token(
    username: str,
    purpose: str = "login",
    expire_minutes: Optional[int] = None,
) -> str:
    """
    Gera um token de uso único, persiste o hash e devolve o valor bruto
    (para compor o link enviado por e-mail).
    """
    minutes = expire_minutes if expire_minutes is not None else settings.MAGIC_LINK_EXPIRE_MINUTES
    raw = secrets.token_urlsafe(32)
    entry = {
        "token_hash": hash_token(raw),
        "username": username,
        "purpose": purpose,
        "expires_at": (_now() + timedelta(minutes=minutes)).isoformat(),
        "used_at": None,
    }
    tokens = cleanup_expired()
    tokens.append(entry)
    _save(tokens)
    return raw


def _find_valid_entry(
    raw_token: str,
    purpose: str,
    tokens: list[dict],
    now: datetime,
) -> Optional[dict]:
    """Localiza entrada válida (não usada, não expirada) sem mutar o store."""
    if not raw_token:
        return None

    token_hash = hash_token(raw_token)
    for entry in tokens:
        if entry.get("token_hash") != token_hash:
            continue
        if entry.get("purpose") != purpose:
            return None
        if entry.get("used_at"):
            return None
        expires_at = _parse_dt(entry.get("expires_at"))
        if not expires_at or expires_at < now:
            return None
        return entry
    return None


def peek_magic_link_token(raw_token: str, purpose: str = "login") -> Optional[str]:
    """
    Valida o token sem consumir (não marca used_at).
    Usado no GET de landing — scanners/prefetch não queimam o link.
    Retorna o username ou None se inválido/expirado/já usado.
    """
    tokens = cleanup_expired()
    entry = _find_valid_entry(raw_token, purpose, tokens, _now())
    return entry.get("username") if entry else None


def consume_magic_link_token(raw_token: str, purpose: str = "login") -> Optional[str]:
    """
    Valida e consome o token (marca used_at).
    Retorna o username em caso de sucesso, ou None se inválido/expirado/já usado.
    """
    tokens = cleanup_expired()
    now = _now()
    entry = _find_valid_entry(raw_token, purpose, tokens, now)
    if not entry:
        return None

    entry["used_at"] = now.isoformat()
    _save(tokens)
    return entry.get("username")
