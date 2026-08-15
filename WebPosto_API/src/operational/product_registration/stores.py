"""Checkpoint e lock do motor permanente."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .checkpoint_migration import read_checkpoint
from .versions import CHECKPOINT_SCHEMA_VERSION


class RegistrationCheckpointStore:
    """Idempotencia por EAN com gravacao atomica. Nao reescreve historico automaticamente."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        return read_checkpoint(self.path)

    def get(self, ean: str) -> dict[str, Any] | None:
        record = self.load().get(ean)
        return record if isinstance(record, dict) else None

    def put(self, ean: str, record: dict[str, Any]) -> None:
        payload = self.load()
        payload[ean] = {
            "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
            "ean": ean,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **record,
        }
        self._atomic_write(payload)

    def _atomic_write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=self.path.name, dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise


class RegistrationLockStore:
    """RUNNING, COMPLETED, PARTIAL e LOCKED. Sem POST previsto, sem trava."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def can_start(self) -> tuple[bool, str]:
        existing = self.load()
        if not existing:
            return True, "NO_LOCK"
        if existing.get("status") == "RUNNING":
            return True, "RESUME_RUNNING"
        return False, f"LOCKED:{existing.get('status')}"

    def persist(
        self,
        *,
        status: str,
        post_count: int,
        created: int,
        skipped: int,
        halted_reason: str | None,
        batch_id: str,
    ) -> None:
        if status == "RUNNING" and post_count == 0 and created == 0:
            # A trava RUNNING so nasce depois do primeiro POST previsto pelo caller.
            pass
        payload = {
            "status": status,
            "batch_id": batch_id,
            "postCount": post_count,
            "createdAndVerified": created,
            "skippedPrePost": skipped,
            "haltedReason": halted_reason,
            "reexecution": "LOCKED" if status in {"COMPLETED", "PARTIAL"} else "OPEN",
            "executedAt": datetime.now(timezone.utc).isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_running_if_posts(self, planned_posts: int, batch_id: str) -> bool:
        if planned_posts <= 0:
            return False
        allowed, _ = self.can_start()
        if not allowed:
            return False
        self.persist(
            status="RUNNING",
            post_count=0,
            created=0,
            skipped=0,
            halted_reason=None,
            batch_id=batch_id,
        )
        return True
