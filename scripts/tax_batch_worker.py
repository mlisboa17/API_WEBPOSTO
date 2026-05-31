"""Background batch worker to validate product catalog tax profiles in bulk.

This is a lightweight asyncio worker that reads product keys from Redis, validates
against a reference fetcher (placeholder) and writes results to a Redis list.
"""
import os
import asyncio
import json
import time
import redis.asyncio as aioredis

from src.infrastructure.tax.matcher_engine import match_and_cache
from src.application.usecases.validate_catalog import validate_catalog

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')


async def reference_fetcher(sku: str) -> dict | None:
    # Placeholder: in production this would call an external tax API
    # Return a mock reference profile
    await asyncio.sleep(0.01)
    return {'sku': sku, 'ncm': '12345678', 'cest': None, 'cfop': '5102', 'cst': '00', 'aliquota_icms': 12.0, 'aliquota_pis': 1.65, 'aliquota_cofins': 7.6}


async def worker(queue_key: str = 'tax:validate:queue', out_key: str = 'tax:validate:results'):
    r = aioredis.from_url(REDIS_URL)
    try:
        while True:
            item = await r.lpop(queue_key)
            if not item:
                await asyncio.sleep(1)
                continue
            data = json.loads(item)
            sku = data.get('sku')
            # do fuzzy match against local catalog cached candidates (placeholder)
            candidates = [{'sku': sku, 'name': data.get('name', sku)}]
            match = await match_and_cache(data.get('name', sku), candidates)
            result = await validate_catalog({'sku': sku, **data}, reference_fetcher)
            await r.rpush(out_key, json.dumps({'sku': sku, 'match': match, 'validation': result}))
    finally:
        await r.close()


def main():
    asyncio.run(worker())


if __name__ == '__main__':
    main()
