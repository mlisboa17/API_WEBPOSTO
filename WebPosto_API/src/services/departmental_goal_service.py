"""Metas departamentais governadas; nenhuma meta fica ativa sem aprovação."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from src.core.management_scope import MANAGEMENT_DEPARTMENTS, is_licensed_company
from src.services.json_file_lock import InterProcessFileLock

ALLOWED_METRICS = {"revenue", "grossMarginValue", "grossMarginPercent"}


class DepartmentalGoalService:
    def __init__(self, path: str | Path = ".runtime/departmental_goals.json") -> None:
        self._path = Path(path)

    def list(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return list(data.get("goals") or []) if isinstance(data, dict) else []

    def save(self, goal: dict[str, Any]) -> dict[str, Any]:
        company = int(goal["companyCode"])
        department, metric = str(goal["department"]), str(goal["metric"])
        if not is_licensed_company(company) or department not in MANAGEMENT_DEPARTMENTS:
            raise ValueError("INVALID_SCOPE")
        if metric not in ALLOWED_METRICS:
            raise ValueError("INVALID_METRIC")
        try:
            value = str(Decimal(str(goal["targetValue"])))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("INVALID_TARGET") from exc
        try:
            period_start = date.fromisoformat(str(goal["periodStart"]))
            period_end = date.fromisoformat(str(goal["periodEnd"]))
        except ValueError as exc:
            raise ValueError("INVALID_PERIOD") from exc
        if period_end < period_start:
            raise ValueError("INVALID_PERIOD")
        approved_by = str(goal.get("approvedBy") or "").strip() or None
        record = {
            "companyCode": company,
            "department": department,
            "metric": metric,
            "targetValue": value,
            "periodStart": period_start.isoformat(),
            "periodEnd": period_end.isoformat(),
            "status": "ACTIVE" if approved_by else "PENDING_APPROVAL",
            "approvedBy": approved_by,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        with InterProcessFileLock(self._path):
            goals = [
                item for item in self.list()
                if not all(item.get(key) == record[key] for key in ("companyCode", "department", "metric", "periodStart", "periodEnd"))
            ]
            goals.append(record)
            payload = {"schemaVersion": 1, "goals": goals}
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temp: Path | None = None
            try:
                with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self._path.parent, delete=False) as handle:
                    json.dump(payload, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                    temp = Path(handle.name)
                os.replace(temp, self._path)
            finally:
                if temp and temp.exists():
                    temp.unlink(missing_ok=True)
        return record
