from __future__ import annotations
import asyncio
import time
import hashlib
from typing import Any, Dict

import httpx
from pydantic import BaseModel, Field, ValidationError


class DashboardFilter(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    from_ts: int | None = None
    to_ts: int | None = None


async def fetch_station(url: str, timeout: float = 2.0) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
    except Exception:
        return {'status': 'offline'}


async def dashboard_aggregator(filter_data: dict, current_user: dict, audit_writer: callable | None = None) -> dict:
    """Aggregate data from multiple stations, enforce RBAC, and write audit trace.

    filter_data: raw input filters (will be validated)
    current_user: dict with at least 'role' and 'id'
    audit_writer: async callable(signature: (actor_id, action, meta_dict))
    """
    # RBAC: only directors and admins allowed
    role = (current_user or {}).get('role')
    if role not in ('director', 'admin'):
        raise PermissionError('requires director role')

    try:
        filters = DashboardFilter.model_validate(filter_data)
    except ValidationError as e:
        raise ValueError(f'Invalid filters: {e}')

    services = [
        'http://localhost:8001/health_metric',
        'http://localhost:8002/health_metric',
        'http://localhost:8003/health_metric',
    ]

    start = time.perf_counter()
    results = await asyncio.gather(*(fetch_station(u) for u in services))
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Prepare aggregated payload
    agg = {'sources': results, 'meta': {'query_ms': round(elapsed_ms, 2)}}

    # Audit trace (async)
    if audit_writer:
        checksum = hashlib.sha256(str(agg).encode('utf-8')).hexdigest()
        await audit_writer(current_user.get('id'), 'dashboard_refresh', {'filters': filters.model_dump(), 'checksum': checksum, 'query_ms': round(elapsed_ms, 2)})

    return agg
