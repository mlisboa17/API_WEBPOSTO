"""Estado de jobs de auditoria no Valkey."""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.infrastructure.cache.redis_pool import get_async_redis

logger = logging.getLogger(__name__)

PREFIX = "audit:job:"
TTL_JOB = 3600


class AuditJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class AuditJobState(BaseModel):
    job_id: str
    status: AuditJobStatus = AuditJobStatus.PENDING
    params: dict[str, Any] = Field(default_factory=dict)
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


def _key(job_id: str) -> str:
    return f"{PREFIX}{job_id}"


async def save_job_state(state: AuditJobState) -> None:
    redis = get_async_redis()
    if redis is None:
        return
    try:
        await redis.setex(_key(state.job_id), TTL_JOB, state.model_dump_json())
    except Exception as exc:
        logger.warning("audit job save: %s", exc)


async def load_job_state(job_id: str) -> Optional[AuditJobState]:
    redis = get_async_redis()
    if redis is None:
        return None
    try:
        raw = await redis.get(_key(job_id))
        if raw:
            return AuditJobState.model_validate_json(raw)
    except Exception as exc:
        logger.debug("audit job load: %s", exc)
    return None
