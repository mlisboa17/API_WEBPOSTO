"""
Pool de conexões Redis assíncrono (cache + locks distribuídos).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

_pool = None
_client = None


def get_redis_pool():
    global _pool
    if _pool is None:
        try:
            from redis.asyncio import ConnectionPool

            _pool = ConnectionPool.from_url(
                settings.redis_url,
                max_connections=20,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2,
            )
            logger.info("Redis async pool criado")
        except Exception as exc:
            logger.warning("Redis async pool indisponível: %s", exc)
            _pool = None
    return _pool


def get_async_redis():
    global _client
    pool = get_redis_pool()
    if pool is None:
        return None
    if _client is None:
        from redis.asyncio import Redis

        _client = Redis(connection_pool=pool)
    return _client


async def redis_ping() -> tuple[bool, str]:
    client = get_async_redis()
    if client is None:
        return False, "unavailable"
    try:
        ok = await client.ping()
        return bool(ok), "ok" if ok else "ping_failed"
    except Exception as exc:
        return False, str(exc)[:120]


@asynccontextmanager
async def redis_lock(
    key: str,
    *,
    ttl_ms: int = 30_000,
    wait_ms: int = 5000,
) -> AsyncIterator[bool]:
    """
    Lock distribuído SET NX PX. Yields True se adquiriu o lock.
  Evita thundering herd ao refrescar cache.
    """
    client = get_async_redis()
    if client is None:
        yield True
        return
    lock_key = f"lock:{key}"
    acquired = False
    try:
        import asyncio

        deadline = asyncio.get_event_loop().time() + (wait_ms / 1000)
        while asyncio.get_event_loop().time() < deadline:
            acquired = await client.set(lock_key, "1", nx=True, px=ttl_ms)
            if acquired:
                break
            await asyncio.sleep(0.05)
        yield bool(acquired)
    finally:
        if acquired:
            try:
                await client.delete(lock_key)
            except Exception:
                pass
