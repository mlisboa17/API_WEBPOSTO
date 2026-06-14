"""F08.2 — Audit trail de execuções de snapshot financeiro."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from src.services.financial_snapshot_service import FINANCIAL_DIR

EXECUTIONS_FILE = FINANCIAL_DIR / "_executions.jsonl"
MAX_MEMORY = 200


class FinancialSnapshotExecutionStore:
    def __init__(self, path: Path = EXECUTIONS_FILE) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._recent: list[dict[str, Any]] = []

    def start(self, snapshot_type: str, *, trigger: str = "scheduler") -> str:
        execution_id = str(uuid.uuid4())
        row = {
            "execution_id": execution_id,
            "snapshot_type": snapshot_type,
            "trigger_type": trigger,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "finished_at": None,
            "success": None,
            "duration_ms": None,
            "record_count": None,
            "source": None,
            "error_type": None,
            "lineage": None,
            "error": None,
        }
        self._append(row)
        return execution_id

    def finish(
        self,
        execution_id: str,
        *,
        success: bool,
        started_at: datetime,
        records: int | None = None,
        error: str | None = None,
        source: str | None = None,
        trigger_type: str | None = None,
        error_type: str | None = None,
        lineage: bool | None = None,
    ) -> dict[str, Any]:
        finished_at = datetime.now()
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        row = {
            "execution_id": execution_id,
            "finished_at": finished_at.isoformat(timespec="seconds"),
            "success": success,
            "duration_ms": duration_ms,
            "record_count": records,
            "records": records,
            "source": source,
            "trigger_type": trigger_type,
            "error_type": error_type,
            "lineage": lineage,
            "error": error,
        }
        self._append(row)
        return row

    def _append(self, row: dict[str, Any]) -> None:
        self._recent.append(row)
        if len(self._recent) > MAX_MEMORY:
            self._recent = self._recent[-MAX_MEMORY:]
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self._path.exists():
            return self._recent[-limit:]
        merged: dict[str, dict[str, Any]] = {}
        try:
            lines = self._path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return self._recent[-limit:]
        for line in lines[-1000:]:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict):
                continue
            exec_id = item.get("execution_id")
            if not exec_id:
                continue
            base = merged.get(exec_id, {"execution_id": exec_id})
            base.update({k: v for k, v in item.items() if v is not None})
            merged[exec_id] = base
        rows = list(merged.values())
        rows.sort(key=lambda r: r.get("finished_at") or r.get("started_at") or "", reverse=True)
        return rows[:limit]

    def dw_rows(self, limit: int = 100) -> list[dict[str, Any]]:
        return [
            {
                "execution_id": row.get("execution_id"),
                "snapshot_type": row.get("snapshot_type"),
                "started_at": row.get("started_at"),
                "finished_at": row.get("finished_at"),
                "success": row.get("success"),
                "duration_ms": row.get("duration_ms"),
                "record_count": row.get("record_count") or row.get("records"),
                "source": row.get("source"),
                "trigger_type": row.get("trigger_type"),
                "error_type": row.get("error_type"),
                "lineage": row.get("lineage"),
            }
            for row in self.list_recent(limit)
        ]


_execution_store: FinancialSnapshotExecutionStore | None = None


def get_execution_store() -> FinancialSnapshotExecutionStore:
    global _execution_store
    if _execution_store is None:
        _execution_store = FinancialSnapshotExecutionStore()
    return _execution_store
