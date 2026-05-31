from __future__ import annotations
import os
import asyncio
import json
from hashlib import sha256
from typing import Any, Dict, List
from decimal import Decimal

import redis.asyncio as aioredis
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from src.application.usecases.tax_recovery import tax_recovery_report

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/webposto')
NCM_CACHE_TTL = 30 * 24 * 3600  # 30 days


def build_audit_checksum(row: Dict[str, Any]) -> str:
    payload = "|".join(
        [
            str(row.get('sku', '')),
            str(row.get('units', '0')),
            str(row.get('price', '0')),
            str(row.get('cost', '0')),
            str(row.get('ncm', '')),
        ]
    )
    return sha256(payload.encode('utf-8')).hexdigest()


async def fetch_sales_chunk(engine_url: str, tenant_id: str, from_ts: int, to_ts: int, limit: int = 10000) -> List[Dict]:
    engine = create_async_engine(engine_url, future=True)
    async with AsyncSession(engine) as session:
        sql = sa.text("""
        SELECT sku,
               SUM(units) as units,
               AVG(price) as price,
               AVG(cost) as cost,
               MAX(COALESCE(ncm, '00000000')) as ncm
        FROM sales
        WHERE tenant_id = :tid AND timestamp >= :from_ts AND timestamp <= :to_ts
        GROUP BY sku
        LIMIT :lim
        """)
        res = await session.execute(sql, {'tid': tenant_id, 'from_ts': from_ts, 'to_ts': to_ts, 'lim': limit})
        rows = res.fetchall()
        await engine.dispose()
        return [
            {
                'sku': r[0],
                'units': int(r[1]),
                'price': float(r[2]),
                'cost': float(r[3]),
                'ncm': r[4],
            }
            for r in rows
        ]


async def cache_ncm_lookup(redis_client, sku: str, lookup_fn) -> Dict:
    key = f'ncm:ref:{sku}'
    raw = await redis_client.get(key)
    if raw:
        return json.loads(raw)
    ref = await lookup_fn(sku)
    if ref:
        await redis_client.set(key, json.dumps(ref, ensure_ascii=False), ex=NCM_CACHE_TTL)
    return ref


async def process_period(tenant_id: str, from_ts: int, to_ts: int, lookup_fn) -> Dict:
    r = aioredis.from_url(REDIS_URL)
    try:
        sales = await fetch_sales_chunk(DATABASE_URL, tenant_id, from_ts, to_ts)
        lookups = await asyncio.gather(*(cache_ncm_lookup(r, s['sku'], lookup_fn) for s in sales))
        enriched = []
        for sale, meta in zip(sales, lookups):
            normalized = dict(sale)
            normalized['sku_meta'] = meta or {}
            normalized['checksum'] = build_audit_checksum(normalized)
            enriched.append(normalized)

        report = await tax_recovery_report(enriched)
        result = {
            'tenant_id': tenant_id,
            'window': {'from_ts': from_ts, 'to_ts': to_ts},
            'rows': len(enriched),
            'cache_hit_ratio': getattr(r, 'hit_ratio', lambda: 0.0)(),
            'report': report,
            'checksums': [row['checksum'] for row in enriched],
        }
        await r.set(
            f'tax:recovery:{tenant_id}:{from_ts}:{to_ts}',
            json.dumps(result, default=str, ensure_ascii=False),
            ex=3600,
        )
        return result
    finally:
        await r.close()
