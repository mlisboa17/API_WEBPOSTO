"""Cache Valkey para auditoria — TTL 15 min, anti thundering herd."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

from src.domain.entities.audit import AuditSession
from src.infrastructure.cache.redis_pool import redis_lock, get_async_redis

logger = logging.getLogger(__name__)

AUDIT_TTL_SECONDS = 900


def audit_cache_key(
    posto_id: str,
    sub_centro: str,
    data_inicio: str,
    data_fim: str,
) -> str:
    raw = f"{posto_id}:{sub_centro}:{data_inicio}:{data_fim}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:20]
    return f"audit:{posto_id}:{sub_centro}:{digest}"


async def get_audit_cached(key: str) -> Optional[AuditSession]:
    redis = get_async_redis()
    if redis is None:
        return None
    try:
        raw = await redis.get(key)
        if raw:
            return AuditSession.model_validate(json.loads(raw))
    except Exception as exc:
        logger.debug("audit cache get: %s", exc)
    return None


async def set_audit_cached(key: str, session: AuditSession) -> None:
    redis = get_async_redis()
    if redis is None:
        return
    try:
        payload = session.model_dump(mode="json")
        await redis.setex(key, AUDIT_TTL_SECONDS, json.dumps(payload, default=str))
    except Exception as exc:
        logger.debug("audit cache set: %s", exc)


async def get_or_reconcile(
    key: str,
    factory,
) -> AuditSession:
    """Lock distribuído + cache 15 min."""
    hit = await get_audit_cached(key)
    if hit:
        return hit.model_copy(update={"cache_hit": True})

    async with redis_lock(key, ttl_ms=60_000, wait_ms=15_000) as acquired:
        if not acquired:
            stale = await get_audit_cached(key)
            if stale:
                return stale.model_copy(update={"cache_hit": True})

        hit2 = await get_audit_cached(key)
        if hit2:
            return hit2.model_copy(update={"cache_hit": True})

        result = await factory()
        await set_audit_cached(key, result)
        return result
