from __future__ import annotations

from collections import OrderedDict
from typing import Optional

from src.infrastructure.cache.valkey_manager import ValkeyManager, get_cache


class ExpenseCategoryCache:
    """LRU local com sincronização opcional no Valkey para categorias frequentes."""

    def __init__(self, capacity: int = 2048, backend: Optional[ValkeyManager] = None) -> None:
        self._capacity = max(capacity, 128)
        self._backend = backend or get_cache()
        self._lru: OrderedDict[str, str] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _put_local(self, key: str, value: str) -> None:
        if key in self._lru:
            self._lru.pop(key)
        self._lru[key] = value
        if len(self._lru) > self._capacity:
            self._lru.popitem(last=False)

    def get(self, description: str) -> Optional[str]:
        key = f"expense:cat:{description.strip().lower()}"
        if key in self._lru:
            self._hits += 1
            value = self._lru.pop(key)
            self._lru[key] = value
            return value

        remote = self._backend.get_json(key)
        if isinstance(remote, dict) and isinstance(remote.get("category"), str):
            self._hits += 1
            value = remote["category"]
            self._put_local(key, value)
            return value

        self._misses += 1
        return None

    def set(self, description: str, category: str, ttl: int = 3600) -> None:
        key = f"expense:cat:{description.strip().lower()}"
        self._put_local(key, category)
        self._backend.set_json(key, {"category": category}, ttl=ttl)

    def stats(self) -> dict[str, float | int]:
        total = self._hits + self._misses
        ratio = (self._hits / total * 100.0) if total else 100.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio_pct": round(ratio, 2),
            "lru_size": len(self._lru),
            "capacity": self._capacity,
        }


_cache: ExpenseCategoryCache | None = None


def get_expense_category_cache() -> ExpenseCategoryCache:
    global _cache
    if _cache is None:
        _cache = ExpenseCategoryCache()
    return _cache
