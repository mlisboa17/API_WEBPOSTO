from __future__ import annotations
import difflib
import os
import json
import asyncio
import redis.asyncio as aioredis
from typing import List, Dict

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CACHE_TTL = 24 * 3600


def fuzzy_score(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


async def match_and_cache(name: str, candidates: List[Dict], ttl: int = CACHE_TTL) -> Dict:
    """Return best match from candidates and cache result in Redis.

    candidates: list of dicts with at least 'sku' and 'name'
    """
    r = aioredis.from_url(REDIS_URL)
    key = f"tax:matcher:{name}"
    try:
        raw = await r.get(key)
        if raw:
            return json.loads(raw)

        best = None
        best_score = 0.0
        for c in candidates:
            s = fuzzy_score(name, c.get('name', ''))
            if s > best_score:
                best = c
                best_score = s

        result = {'query': name, 'match': best, 'score': best_score}
        await r.set(key, json.dumps(result, ensure_ascii=False), ex=ttl)
        return result
    finally:
        await r.close()
