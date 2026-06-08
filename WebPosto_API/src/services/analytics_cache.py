from __future__ import annotations

import time
from typing import Any, Optional

# Dict-based in-memory cache storage: holds {key: (expire_at, value)}
_cache: dict[str, tuple[float, Any]] = {}


def build_cache_key(endpoint: str, filters: Any) -> str:
    """
    Builds a cache key following the SPRINT 17 specification:
    Key template: endpoint + dataInicial + dataFinal + empresaCodigo + filial
    """
    data_inicial = ""
    data_final = ""
    empresa_codigo = ""
    filial = ""

    if isinstance(filters, dict):
        data_inicial = str(filters.get("data_inicial") or filters.get("dataInicial") or "")
        data_final = str(filters.get("data_final") or filters.get("dataFinal") or "")
        empresa_codigo = str(filters.get("empresa_codigo") or filters.get("empresaCodigo") or "")
        filial = str(filters.get("filial") or "")
    elif filters is not None:
        data_inicial = str(getattr(filters, "data_inicial", None) or getattr(filters, "dataInicial", None) or "")
        data_final = str(getattr(filters, "data_final", None) or getattr(filters, "dataFinal", None) or "")
        empresa_codigo = str(getattr(filters, "empresa_codigo", None) or getattr(filters, "empresaCodigo", None) or "")
        filial = str(getattr(filters, "filial", None) or "")

    return f"{endpoint}:{data_inicial}:{data_final}:{empresa_codigo}:{filial}"


def get_cache(key: str) -> Optional[Any]:
    """Retrieves the value from cache if it has not expired yet."""
    now = time.time()
    if key in _cache:
        expire_at, value = _cache[key]
        if now < expire_at:
            return value
        else:
            del _cache[key]
    return None


def set_cache(key: str, value: Any, ttl: float = 60.0) -> None:
    """Caches a value with a specific TTL (in seconds)."""
    _cache[key] = (time.time() + ttl, value)


def clear_cache(pattern: Optional[str] = None) -> None:
    """Clears the whole cache or all keys containing the specified pattern."""
    if not pattern:
        _cache.clear()
        return
    to_delete = [k for k in _cache if pattern in k]
    for k in to_delete:
        _cache.pop(k, None)
