"""
Rate limit em memória (janela deslizante) para endpoints sensíveis.

Processo único (uvicorn sem workers) — suficiente para este app. Se escalar
para múltiplos workers, migrar para Redis.
"""
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, status

_hits: dict[str, deque] = defaultdict(deque)
_lock = Lock()


def check_rate_limit(key: str, max_hits: int, window_seconds: int) -> None:
    """Levanta 429 se `key` excedeu `max_hits` dentro de `window_seconds`."""
    now = time.monotonic()
    with _lock:
        bucket = _hits[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= max_hits:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas tentativas. Aguarde alguns minutos e tente novamente.",
            )
        bucket.append(now)


def reset_rate_limits() -> None:
    """Uso em testes."""
    with _lock:
        _hits.clear()
