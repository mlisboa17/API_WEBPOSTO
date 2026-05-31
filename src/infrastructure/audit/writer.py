import os
import json
import time
import redis.asyncio as aioredis

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')


async def audit_writer(actor_id: str, action: str, meta: dict):
    """Write audit entry to Redis list as fallback storage for immutability.

    In production this should persist to Postgres append-only table with WAL.
    """
    r = aioredis.from_url(REDIS_URL)
    try:
        entry = {'actor': actor_id, 'action': action, 'meta': meta, 'ts': int(time.time() * 1000)}
        await r.rpush('audit:entries', json.dumps(entry, ensure_ascii=False))
    finally:
        await r.close()
