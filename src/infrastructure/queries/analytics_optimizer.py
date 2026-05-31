from __future__ import annotations
from typing import List, Dict
import asyncio
from decimal import Decimal
import time

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from src.infrastructure.finance.rateio_engine import quantize4


async def query_margin_report(engine_url: str, tenant_id: str, from_ts: int, to_ts: int) -> List[Dict]:
    """Run optimized SQL to fetch SKU aggregates.

    This function is conservative: it builds a parameterized query that expects
    indexes on tenant_id and timestamp for performance on Postgres 17.
    """
    engine = create_async_engine(engine_url, future=True)
    async with AsyncSession(engine) as session:
        sql = sa.text("""
        SELECT sku, SUM(units) AS units, SUM(price * units) AS revenue, SUM(cost * units) AS cost
        FROM sales
        WHERE tenant_id = :tid AND timestamp >= :from_ts AND timestamp <= :to_ts
        GROUP BY sku
        ORDER BY SUM(price * units) DESC
        LIMIT 10000
        """)
        start = time.perf_counter()
        res = await session.execute(sql, {'tid': tenant_id, 'from_ts': from_ts, 'to_ts': to_ts})
        rows = res.fetchall()
        elapsed = (time.perf_counter() - start) * 1000
        # attach performance metric
        return [{'sku': r[0], 'units': int(r[1]), 'revenue': str(quantize4(Decimal(r[2]))), 'cost': str(quantize4(Decimal(r[3]))), 'query_ms': round(elapsed,2)} for r in rows]
