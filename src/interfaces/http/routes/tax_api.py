from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
import redis.asyncio as aioredis
import os
import json
from typing import List

router = APIRouter()

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
QUEUE_KEY = 'tax:validate:queue'
OUT_KEY = 'tax:validate:results'


async def sse_sync_generator(channel: str = 'tax:sync'):
    r = aioredis.from_url(REDIS_URL)
    pub = r.pubsub()
    try:
        await pub.subscribe(channel)
        async for msg in pub.listen():
            if msg and msg.get('type') == 'message':
                data = msg.get('data')
                if isinstance(data, bytes):
                    yield f"data: {data.decode()}\n\n"
    finally:
        try:
            await pub.unsubscribe(channel)
            await pub.close()
        except Exception:
            pass


@router.get('/tax/sync/stream')
async def tax_sync_stream():
    return StreamingResponse(sse_sync_generator(), media_type='text/event-stream')


@router.post('/tax/enqueue')
async def tax_enqueue(items: List[dict]):
    """Enqueue items for tax validation worker; items is list of dicts containing sku and name."""
    r = aioredis.from_url(REDIS_URL)
    try:
        for it in items:
            await r.rpush(QUEUE_KEY, json.dumps(it, ensure_ascii=False))
        return JSONResponse({'enqueued': len(items)})
    finally:
        await r.close()


@router.post('/tax/homologate')
async def tax_homologate(skus: List[str]):
    r = aioredis.from_url(REDIS_URL)
    try:
        for s in skus:
            await r.sadd('tax:homologated', s)
        return JSONResponse({'homologated': len(skus)})
    finally:
        await r.close()
