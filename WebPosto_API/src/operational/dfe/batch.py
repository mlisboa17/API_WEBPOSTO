"""Controle simples de lotes de importação (progresso em memória)."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

_lock = threading.RLock()
_BATCHES: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_batch_id() -> str:
    return f"dfe_batch_{uuid.uuid4().hex[:12]}"


def create_batch(company_code: int, source_files: int) -> dict[str, Any]:
    bid = new_batch_id()
    doc = {
        "batchId": bid,
        "companyCode": company_code,
        "status": "QUEUED",
        "sourceFiles": source_files,
        "total": 0,
        "processed": 0,
        "successes": 0,
        "duplicates": 0,
        "failures": 0,
        "ignored": 0,
        "currentItem": None,
        "startedAt": _now(),
        "updatedAt": _now(),
        "completedAt": None,
        "webpostoWrites": 0,
        "sefazQueries": 0,
    }
    with _lock:
        _BATCHES[bid] = doc
    return doc


def update_batch(batch_id: str, **kwargs: Any) -> dict[str, Any]:
    with _lock:
        doc = _BATCHES.get(batch_id)
        if not doc:
            raise KeyError(batch_id)
        doc.update(kwargs)
        doc["updatedAt"] = _now()
        return dict(doc)


def get_batch(batch_id: str) -> dict[str, Any] | None:
    with _lock:
        doc = _BATCHES.get(batch_id)
        return dict(doc) if doc else None


def reset_batches_for_tests() -> None:
    with _lock:
        _BATCHES.clear()
