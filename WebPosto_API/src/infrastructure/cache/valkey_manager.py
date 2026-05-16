"""
Valkey/Redis cache — JSON get/set com TTL para consultas WebPosto.
Fallback em memória quando o broker não estiver disponível.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Optional

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class ValkeyManager:
    """Cache JSON com hit ratio alto para relatórios operacionais (TTL padrão 60s)."""

    def __init__(self, url: Optional[str] = None, default_ttl: int = 60) -> None:
        self.default_ttl = default_ttl
        self._redis = None
        self._memory: dict[str, tuple[float, str]] = {}
        self._hits = 0
        self._misses = 0
        redis_url = url or settings.redis_url
        try:
            import redis

            client = redis.from_url(redis_url, decode_responses=True, socket_timeout=2)
            client.ping()
            self._redis = client
            logger.info("Valkey/Redis conectado: %s", redis_url.split("@")[-1])
        except Exception as exc:
            logger.warning("Cache remoto indisponível — memória local: %s", exc)

    def _purge_memory(self) -> None:
        now = time.time()
        expired = [k for k, (exp, _) in self._memory.items() if exp <= now]
        for k in expired:
            del self._memory[k]

    @staticmethod
    def cache_key(prefix: str, path: str, query: dict[str, Any]) -> str:
        raw = json.dumps({"p": path, "q": query}, sort_keys=True, default=str)
        digest = hashlib.sha256(raw.encode()).hexdigest()[:24]
        return f"wp:{prefix}:{digest}"

    def get_json(self, key: str) -> Optional[Any]:
        if self._redis:
            try:
                raw = self._redis.get(key)
                if raw is not None:
                    self._hits += 1
                    return json.loads(raw)
            except Exception as exc:
                logger.debug("get_json redis falhou: %s", exc)
        self._purge_memory()
        entry = self._memory.get(key)
        if entry and entry[0] > time.time():
            self._hits += 1
            return json.loads(entry[1])
        self._misses += 1
        return None

    def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        ttl = ttl if ttl is not None else self.default_ttl
        payload = json.dumps(value, default=str)
        if self._redis:
            try:
                self._redis.setex(key, ttl, payload)
                return True
            except Exception as exc:
                logger.debug("set_json redis falhou: %s", exc)
        self._memory[key] = (time.time() + ttl, payload)
        return True

    @property
    def hit_ratio(self) -> float:
        total = self._hits + self._misses
        return (self._hits / total * 100.0) if total else 0.0

    def stats(self) -> dict[str, Any]:
        return {
            "backend": "redis" if self._redis else "memory",
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio_pct": round(self.hit_ratio, 2),
        }


_cache: Optional[ValkeyManager] = None


def get_cache() -> ValkeyManager:
    global _cache
    if _cache is None:
        _cache = ValkeyManager()
    return _cache
