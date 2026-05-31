"""
Verificações de saúde: banco, Redis, API externa.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict

from src.infrastructure.cache.redis_pool import redis_ping
from src.infrastructure.cache.valkey_manager import get_cache
from src.infrastructure.config.settings import settings
from src.infrastructure.http.http_client import ExternalHttpClient

logger = logging.getLogger(__name__)


def check_database() -> Dict[str, Any]:
    url = os.getenv("DATABASE_URL", settings.database_url)
    if "sqlite" in url.lower():
        return {"status": "ok", "backend": "sqlite", "detail": "local file"}
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(url.replace("+asyncpg", "").replace("aiosqlite", ""))
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "backend": "postgres"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)[:200]}


async def check_redis() -> Dict[str, Any]:
    ok_async, detail = await redis_ping()
    cache = get_cache()
    stats = cache.stats()
    pool_active = ok_async
    return {
        "status": "ok" if pool_active or stats.get("backend") == "memory" else "degraded",
        "valkey_pool_active": pool_active,
        "async_pool": detail,
        "cache_backend": stats.get("backend"),
        "hit_ratio_pct": stats.get("hit_ratio_pct"),
    }


async def check_external_api(base_url: str) -> Dict[str, Any]:
    client = ExternalHttpClient(base_url)
    t0 = time.perf_counter()
    reachable, status, code = await client.head_connectivity()
    ms = int((time.perf_counter() - t0) * 1000)
    return {
        "status": "ok" if reachable else "error",
        "http_status": status,
        "elapsed_ms": ms,
        "base_url": base_url,
    }


async def run_health_checks(base_url: str, *, has_api_key: bool) -> Dict[str, Any]:
    db = check_database()
    redis = await check_redis()
    external = await check_external_api(base_url)

    parts_ok = [
        db.get("status") == "ok",
        redis.get("status") in ("ok", "degraded"),
        external.get("status") == "ok",
        has_api_key,
    ]
    overall = "healthy" if all(parts_ok) else "degraded" if has_api_key else "attention"

    return {
        "status": overall,
        "database": db,
        "redis": redis,
        "external_api": external,
        "api_key_loaded": has_api_key,
        "circuit_breaker": __import__(
            "src.infrastructure.resilience.circuit_breaker",
            fromlist=["get_webposto_circuit_breaker"],
        ).get_webposto_circuit_breaker().snapshot(),
    }
