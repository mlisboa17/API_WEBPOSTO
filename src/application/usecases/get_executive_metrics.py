from decimal import Decimal
import json
from typing import Any

from fastapi import HTTPException

from src.domain.entities.audit import MetricSnapshot, Role
from src.infrastructure.config.settings import settings

import asyncio


async def get_executive_metrics(db_session, cache, current_user) -> dict[str, Any]:
    """Aggregate executive metrics across multiple stations.

    - Enforces RBAC: only Role.DIRECTOR allowed.
    - Uses cache (TTL 30s) to reduce DB load.
    - Returns serializable dict with Decimal values as strings.
    """

    # RBAC strict check
    if not getattr(current_user, "role", None) == Role.DIRECTOR.value:
        raise HTTPException(status_code=403, detail="Forbidden: director role required")

    cache_key = "executive:metrics:aggregate:v1"
    # Try cache (assumes `cache` is aioredis/redis.asyncio client)
    try:
        cached = await cache.get(cache_key)
        if cached:
            # Support both dict (RedisCacheAdapter) and JSON string
            if isinstance(cached, (str, bytes)):
                return json.loads(cached)
            return cached
    except Exception:
        cached = None

    # Simulate parallel reads from multiple stations (replace with real queries)
    async def _fetch_station(name: str) -> MetricSnapshot:
        # Placeholder aggregation — in production, run optimized SQL/aggregations
        await asyncio.sleep(0)  # yield
        return MetricSnapshot(
            source=name,
            total_sales=Decimal("10000.0000"),
            net_margin=Decimal("1250.0000"),
            tax_collected=Decimal("800.0000"),
        )

    stations = ["Casa Caiada", "VIP", "Real"]
    tasks = [_fetch_station(s) for s in stations]
    results = await asyncio.gather(*tasks)

    # Consolidate
    total_sales = sum((r.total_sales for r in results), Decimal("0.0000"))
    net_margin = sum((r.net_margin for r in results), Decimal("0.0000"))
    tax_collected = sum((r.tax_collected for r in results), Decimal("0.0000"))

    payload = {
        "total_sales": str(total_sales.quantize(Decimal("0.0001"))),
        "net_margin": str(net_margin.quantize(Decimal("0.0001"))),
        "tax_collected": str(tax_collected.quantize(Decimal("0.0001"))),
        "by_station": [r.model_dump() for r in results],
    }

    # Store in cache TTL 30s
    try:
        # RedisCacheAdapter expects a dict; set with adapter TTL
        await cache.set(cache_key, payload, ttl=None)
    except Exception:
        # Fallback: if adapter expects raw set method
        try:
            await cache.set(cache_key, json.dumps(payload), ex=30)
        except Exception:
            pass

    return payload
