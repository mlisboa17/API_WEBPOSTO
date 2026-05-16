from fastapi import APIRouter, Depends, Request
from typing import Dict

from src.interfaces.http.dependencies import get_db, get_event_bus, get_webposto_client, get_current_user
from src.infrastructure.cache.redis_adapter import RedisCacheFactory
from src.application.usecases.get_executive_metrics import get_executive_metrics

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/executive")
async def executive_metrics(request: Request, current_user: Dict = Depends(get_current_user)):
    """Return consolidated executive metrics (RBAC enforced)."""
    # Create cache client
    cache = await RedisCacheFactory.criar_cache(host="valkey" if True else "redis", port=6379)
    try:
        payload = await get_executive_metrics(None, cache, current_user)
        return payload
    finally:
        await cache.disconnect()


@router.get("/stream")
async def stream_metrics():
    """SSE endpoint stub for server-sent metrics. In production, replace with proper event streaming."""
    # Minimal stub: return 204; frontend will fallback to polling
    return {"status": "stream-stub"}
