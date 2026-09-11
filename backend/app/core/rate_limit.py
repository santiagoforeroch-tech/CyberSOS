"""Límite ligero para el formulario público; no sustituye controles perimetrales."""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException

_attempts: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def limit_public_report(client_ip: str, limit: int, window_seconds: int) -> None:
    now = monotonic()
    with _lock:
        attempts = _attempts[client_ip]
        while attempts and attempts[0] <= now - window_seconds:
            attempts.popleft()
        if len(attempts) >= limit:
            raise HTTPException(429, "Has enviado demasiados reportes. Espera unos minutos e inténtalo de nuevo.")
        attempts.append(now)
