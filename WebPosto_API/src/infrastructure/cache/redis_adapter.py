"""
Adaptador Redis/Valkey — delega ao ValkeyManager unificado (compat metrics route).
"""

from __future__ import annotations

from typing import Any, Optional

from src.infrastructure.cache.valkey_manager import ValkeyManager, get_cache


class RedisCacheFactory:
    """Factory usada pelas rotas legadas de métricas."""

    @staticmethod
    async def criar_cache(
        host: str = "127.0.0.1",
        port: int = 6379,
        **_: Any,
    ) -> "_RedisCacheAdapter":
        return _RedisCacheAdapter(get_cache())


class _RedisCacheAdapter:
    def __init__(self, manager: ValkeyManager) -> None:
        self._m = manager

    async def get(self, key: str) -> Optional[Any]:
        return self._m.get_json(key)

    async def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        return self._m.set_json(key, value, ttl=ttl)

    async def disconnect(self) -> None:
        pass
