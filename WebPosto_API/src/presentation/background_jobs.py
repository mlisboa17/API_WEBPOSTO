"""
Jobs em memória para rotas 202 Accepted (consultas pesadas Adelaide/WebPosto).
"""

from __future__ import annotations

import asyncio
import time
import uuid
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class JobRecord(BaseModel):
    id: str
    status: JobStatus = JobStatus.PENDING
    created_at: float = Field(default_factory=time.time)
    finished_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None


_store: Dict[str, JobRecord] = {}
_lock = asyncio.Lock()


async def create_job() -> str:
    job_id = str(uuid.uuid4())
    async with _lock:
        _store[job_id] = JobRecord(id=job_id)
    return job_id


async def get_job(job_id: str) -> Optional[JobRecord]:
    async with _lock:
        return _store.get(job_id)


async def run_job(job_id: str, coro) -> None:
    async with _lock:
        rec = _store.get(job_id)
        if rec:
            rec.status = JobStatus.RUNNING
    try:
        result = await coro
        async with _lock:
            rec = _store.get(job_id)
            if rec:
                rec.status = JobStatus.DONE
                rec.result = result
                rec.finished_at = time.time()
    except Exception as exc:
        async with _lock:
            rec = _store.get(job_id)
            if rec:
                rec.status = JobStatus.FAILED
                rec.error = str(exc)[:500]
                rec.finished_at = time.time()
