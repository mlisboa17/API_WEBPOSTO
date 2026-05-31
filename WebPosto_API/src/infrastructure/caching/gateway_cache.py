from __future__ import annotations

import time
from typing import Any, Optional


class GatewayCache:
    """Cache em memória para resposta por posto_id + data_consulta (TTL curto)."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at <= time.time():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time() + self._ttl_seconds, value)


_cache: GatewayCache | None = None


def get_gateway_cache() -> GatewayCache:
    global _cache
    if _cache is None:
        _cache = GatewayCache(ttl_seconds=300)
    return _cache
