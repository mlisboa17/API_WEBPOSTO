from __future__ import annotations
import os
import asyncio
from decimal import Decimal, getcontext, ROUND_DOWN
import hashlib
import json
import time

import redis.asyncio as aioredis

# Set decimal precision context: enough digits, we'll quantize to 4 places
getcontext().prec = 18

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CACHE_TTL = 30  # seconds


def quantize4(d: Decimal) -> Decimal:
    return d.quantize(Decimal('0.0001'), rounding=ROUND_DOWN)


def normalize_share_values(values: list[Decimal]) -> list[Decimal]:
    """Given list of Decimal shares, normalize them so they sum exactly to 100.0000%.

    Strategy: quantize down each value, compute residual and add leftover to largest share.
    """
    if not values:
        return []
    quantized = [quantize4(v) for v in values]
    total = sum(quantized)
    target = Decimal('100.0000')
    residual = target - total
    if residual == 0:
        return quantized

    # add residual to the largest entry to avoid fractional splitting
    max_idx = max(range(len(quantized)), key=lambda i: quantized[i])
    quantized[max_idx] = quantize4(quantized[max_idx] + residual)
    # final adjust in case of rounding weirdness
    final_total = sum(quantized)
    if final_total != target:
        # last resort: adjust difference to largest again
        diff = target - final_total
        quantized[max_idx] = quantize4(quantized[max_idx] + diff)
    return quantized


def sha256_checksum(record: dict) -> str:
    s = json.dumps(record, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


async def cached_rateio(key: str, compute_fn, ttl: int = CACHE_TTL):
    r = aioredis.from_url(REDIS_URL)
    try:
        raw = await r.get(key)
        if raw:
            return json.loads(raw)
        result = await compute_fn()
        await r.set(key, json.dumps(result), ex=ttl)
        return result
    finally:
        try:
            await r.close()
        except Exception:
            pass


async def compute_rateio(shares: dict[str, float] | dict[str, Decimal]) -> dict:
    """Compute rateio distribution for a dict of {unit: value}.

    Returns distribution percentages with Decimal(12,4) precision and checksum.
    """
    # convert to Decimal
    decs = [Decimal(str(v)) for v in shares.values()]
    total = sum(decs) if decs else Decimal('0')
    if total == 0:
        distribution = {k: Decimal('0.0000') for k in shares.keys()}
    else:
        raw_percent = [(Decimal(str(v)) / total) * Decimal('100') for v in shares.values()]
        normalized = normalize_share_values(raw_percent)
        distribution = {k: normalized[i] for i, k in enumerate(shares.keys())}

    # prepare result
    result = {
        'distribution': {k: f"{v:.4f}" for k, v in distribution.items()},
        'checksum': sha256_checksum({'distribution': {k: f"{v:.4f}" for k, v in distribution.items()}}),
        'timestamp': int(time.time() * 1000),
    }
    return result
