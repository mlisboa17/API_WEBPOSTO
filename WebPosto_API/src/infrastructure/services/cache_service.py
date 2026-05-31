"""
Cache adaptativo Valkey — TTL por tipo de dado (Grok).
Tanques: 60s | Pagamentos/consolidados: 300s | Relatórios gerais: 300s
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from src.infrastructure.cache.redis_pool import redis_lock
from src.infrastructure.cache.valkey_manager import ValkeyManager, get_cache

logger = logging.getLogger(__name__)

TTL_TANQUE = 60
TTL_PAGAMENTO = 300
TTL_RELATORIO = 300
TTL_DEFAULT = 300


class CacheService:
    def __init__(self, backend: Optional[ValkeyManager] = None) -> None:
        self._cache = backend or get_cache()

    @staticmethod
    def ttl_for(namespace: str) -> int:
        ns = namespace.lower()
        if "tanque" in ns or "estoque" in ns or "volume" in ns:
            return TTL_TANQUE
        if "pagamento" in ns or "caixa" in ns or "forma" in ns:
            return TTL_PAGAMENTO
        if "relatorio" in ns or "adelaide" in ns or "venda" in ns or "proxy" in ns:
            return TTL_RELATORIO
        return TTL_DEFAULT

    def get_json(self, key: str) -> Optional[Any]:
        return self._cache.get_json(key)

    def set_json(self, key: str, value: Any, *, namespace: str = "default") -> None:
        ttl = self.ttl_for(namespace)
        self._cache.set_json(key, value, ttl=ttl)

    def cache_key(self, prefix: str, path: str, query: dict) -> str:
        return self._cache.cache_key(prefix, path, query)

    async def get_or_set(
        self,
        namespace: str,
        cache_key: str,
        factory: Callable[[], Any],
    ) -> Any:
        """Thundering herd: lock distribuído + TTL adaptativo."""
        hit = self.get_json(cache_key)
        if hit is not None:
            return hit

        async with redis_lock(cache_key, ttl_ms=30_000, wait_ms=8_000) as acquired:
            if not acquired:
                stale = self.get_json(cache_key)
                if stale is not None:
                    return stale

            hit2 = self.get_json(cache_key)
            if hit2 is not None:
                return hit2

            value = factory()
            if hasattr(value, "__await__"):
                value = await value
            self.set_json(cache_key, value, namespace=namespace)
            return value


_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
