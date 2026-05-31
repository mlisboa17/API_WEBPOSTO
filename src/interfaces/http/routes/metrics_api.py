from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import asyncio
import json
import os
import redis.asyncio as aioredis

from src.infrastructure.finance.rateio_engine import compute_rateio
from src.infrastructure.audit.writer import audit_writer

router = APIRouter(prefix="/api")

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')


async def sse_generator(channel_name: str):
    r = aioredis.from_url(REDIS_URL)
    try:
        pub = r.pubsub()
        await pub.subscribe(channel_name)
        async for message in pub.listen():
            if message is None:
                continue
            if message.get('type') == 'message':
                data = message.get('data')
                if isinstance(data, bytes):
                    yield f"data: {data.decode()}\n\n"
    finally:
        try:
            await pub.unsubscribe(channel_name)
            await pub.close()
        except Exception:
            pass


@router.get('/metrics/stream')
async def metrics_stream():
    """SSE stream for executive metrics publishing Redis pubsub 'executive:metrics'"""
    return StreamingResponse(sse_generator('executive:metrics'), media_type='text/event-stream')


@router.post('/metrics/publish')
async def metrics_publish(payload: dict):
    """Publish a metrics payload to Redis pubsub and audit the publish."""
    r = aioredis.from_url(REDIS_URL)
    try:
        data = json.dumps(payload, ensure_ascii=False)
        await r.publish('executive:metrics', data)
        # write audit
        await audit_writer(payload.get('author', 'system'), 'metrics_publish', {'payload': payload})
        return JSONResponse({'published': True})
    finally:
        await r.close()


@router.get('/margins')
async def get_margins(tenant: str = 'Grupo Lisboa'):
    """Return cached rateio or compute from Redis fallback."""
    r = aioredis.from_url(REDIS_URL)
    try:
        raw = await r.get(f'rateio:{tenant}')
        if raw:
            return JSONResponse(content=json.loads(raw))
        # fallback compute: read sample shares from redis
        raw_shares = await r.get(f'shares:{tenant}')
        if not raw_shares:
            raise HTTPException(status_code=404, detail='No shares found')
        shares = json.loads(raw_shares)
        result = await compute_rateio(shares)
        await r.set(f'rateio:{tenant}', json.dumps(result), ex=30)
        return JSONResponse(content=result)
    finally:
        await r.close()
