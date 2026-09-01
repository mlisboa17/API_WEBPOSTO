"""D02 — Persistência de estado de conferência (justificativas imutáveis)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.domain.reconciliation.models import JustificationCategory, JustificationRecord, ReconciliationStatus
from src.services.snapshot_store import safe_filename


class ReconciliationStateStore:
    """Estado de conferência por tenant/período — append-only para justificativas."""

    def __init__(self, output_dir: str | Path = "snapshots/reconciliation_state") -> None:
        self._dir = Path(output_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self._dir / f"{safe_filename(key)}.json"

    def load(self, key: str) -> dict[str, Any]:
        path = self._path(key)
        if not path.exists():
            return {"items": {}, "justifications": {}}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"items": {}, "justifications": {}}

    def save(self, key: str, data: dict[str, Any]) -> None:
        self._path(key).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def state_key(empresa: str | int | None, data_inicial: str, data_final: str) -> str:
        return f"recon:{empresa or 'all'}:{data_inicial}:{data_final}"

    def get_item_state(self, key: str, item_id: str) -> dict[str, Any]:
        data = self.load(key)
        return (data.get("items") or {}).get(item_id) or {}

    def set_item_status(self, key: str, item_id: str, status: ReconciliationStatus, user: str | None = None) -> None:
        data = self.load(key)
        items = data.setdefault("items", {})
        row = items.setdefault(item_id, {})
        row["status"] = status.value
        row["updatedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if user:
            row["responsibleUser"] = user
        self.save(key, data)

    def append_justification(
        self,
        key: str,
        item_id: str,
        reason_category: JustificationCategory,
        description: str,
        responsible_user: str,
        expected_resolution_date: str | None = None,
        created_by: str | None = None,
    ) -> JustificationRecord:
        data = self.load(key)
        just_map = data.setdefault("justifications", {})
        history = just_map.setdefault(item_id, [])
        record = JustificationRecord(
            id=f"JUST-{uuid.uuid4().hex[:10].upper()}",
            reasonCategory=reason_category,
            description=description,
            expectedResolutionDate=expected_resolution_date,
            responsibleUser=responsible_user,
            createdAt=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            createdBy=created_by,
        )
        history.append(record.model_dump())
        items = data.setdefault("items", {})
        row = items.setdefault(item_id, {})
        row["status"] = ReconciliationStatus.JUSTIFIED.value
        row["updatedAt"] = record.createdAt
        row["responsibleUser"] = responsible_user
        self.save(key, data)
        return record

    def list_justifications(self, key: str, item_id: str) -> list[JustificationRecord]:
        data = self.load(key)
        raw = (data.get("justifications") or {}).get(item_id) or []
        return [JustificationRecord(**r) for r in raw if isinstance(r, dict)]

    def list_cash_destinations(self, key: str) -> list[dict[str, Any]]:
        data = self.load(key)
        rows = data.get("cashDestinations") or {}
        return list(rows.values()) if isinstance(rows, dict) else []

    def set_cash_destination(self, key: str, company: str, movement_date: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self.load(key)
        rows = data.setdefault("cashDestinations", {})
        row_key = f"{company}:{movement_date}"
        previous = rows.get(row_key) or {}
        history = list(previous.get("history") or [])
        if previous:
            history.append({k: v for k, v in previous.items() if k != "history"})
        record = {
            **payload,
            "id": row_key,
            "company": company,
            "movementDate": movement_date,
            "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "history": history,
        }
        rows[row_key] = record
        self.save(key, data)
        return record
