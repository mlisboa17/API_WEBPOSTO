"""
Cache em camadas — TTL curto (60s) para dashboard, longo (300s) para catálogo.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Callable, Optional

from src.infrastructure.cache.redis_pool import get_async_redis

logger = logging.getLogger(__name__)

TTL_DASHBOARD = 60
TTL_CATALOG = 300


def _key(namespace: str, raw: str) -> str:
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"wp:{namespace}:{digest}"


async def get_or_set(
    namespace: str,
    cache_key: str,
    factory: Callable[[], Any],
    ttl: int = TTL_DASHBOARD,
) -> Any:
    """Tenta Redis; em falha executa factory sem cache."""
    redis = get_async_redis()
    if redis is None:
        return await _call(factory)

    key = _key(namespace, cache_key)
    try:
        hit = await redis.get(key)
        if hit is not None:
            return json.loads(hit)
    except Exception as e:
        logger.debug("cache get falhou: %s", e)

    value = await _call(factory)
    try:
        await redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.debug("cache set falhou: %s", e)
    return value


async def invalidate(namespace: str, cache_key: str) -> None:
    redis = get_async_redis()
    if redis is None:
        return
    try:
        await redis.delete(_key(namespace, cache_key))
    except Exception:
        pass


async def _call(factory: Callable[[], Any]) -> Any:
    result = factory()
    if hasattr(result, "__await__"):
        return await result
    return result
