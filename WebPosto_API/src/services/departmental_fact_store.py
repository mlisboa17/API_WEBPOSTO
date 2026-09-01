"""Persistência atômica dos lotes departamentais materializados."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Tipo não serializável: {type(value).__name__}")


@lru_cache(maxsize=64)
def _load_json_file(path: str, modified_ns: int, size: int) -> dict[str, Any] | None:
    """Lê JSON uma vez por versão física do arquivo."""
    del modified_ns, size
    try:
        payload = json.loads(Path(path).read_bytes())
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


class DepartmentalFactStore:
    def __init__(self, output_dir: str | Path = ".runtime/departmental_facts") -> None:
        self._output_dir = Path(output_dir)

    @staticmethod
    def key(company_code: int, day: str) -> str:
        safe_day = day.replace("/", "-").replace("\\", "-")
        return f"departmental-facts_{int(company_code)}_{safe_day}"

    def _path(self, company_code: int, day: str) -> Path:
        return self._output_dir / f"{self.key(company_code, day)}.json"

    def save(self, result: dict[str, Any]) -> Path:
        company_code = int(result["companyCode"])
        day = str(result["day"])
        payload = {
            "schemaVersion": 1,
            "savedAt": datetime.now(timezone.utc).isoformat(),
            "data": result,
        }
        content = json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        target = self._path(company_code, day)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self._output_dir,
                prefix=f".{target.stem}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                temp_path = Path(handle.name)
            os.replace(temp_path, target)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)
        return target

    def load(self, company_code: int, day: str) -> dict[str, Any] | None:
        path = self._path(company_code, day)
        try:
            stat = path.stat()
        except OSError:
            return None
        return _load_json_file(str(path.resolve()), stat.st_mtime_ns, stat.st_size)

    def list_days(self, company_code: int) -> list[str]:
        """Lista somente materializações válidas da empresa, sem confiar no nome do arquivo."""
        if not self._output_dir.is_dir():
            return []
        prefix = f"departmental-facts_{int(company_code)}_"
        days: list[str] = []
        for path in self._output_dir.glob(f"{prefix}*.json"):
            raw = path.stem.removeprefix(prefix)
            try:
                day = date.fromisoformat(raw).isoformat()
            except ValueError:
                continue
            stored = self.load(company_code, day)
            data = (stored or {}).get("data") or {}
            if int(data.get("companyCode") or 0) == int(company_code) and data.get("day") == day:
                days.append(day)
        return sorted(set(days))

    def quality_summary(self, company_code: int, day: str) -> dict[str, Any] | None:
        stored = self.load(company_code, day)
        if not stored:
            return None
        data = stored.get("data") or {}
        batch_summary: dict[str, Any] = {}
        for name, batch in (data.get("batches") or {}).items():
            batch_summary[name] = {
                "classified": len(batch.get("facts") or []),
                "quarantined": len(batch.get("quarantine") or []),
                "rejectedUnlicensed": int(batch.get("rejected_unlicensed") or 0),
                "duplicatesRemoved": int(batch.get("duplicates_removed") or 0),
                "identityConflicts": int(batch.get("identity_conflicts") or 0),
                "sourceTotal": batch.get("source_total", "0"),
                "reconciledTotal": batch.get("reconciled_total", "0"),
                "reconciliationDifference": batch.get("reconciliation_difference", "0"),
            }
        return {
            "schemaVersion": stored.get("schemaVersion"),
            "savedAt": stored.get("savedAt"),
            "companyCode": data.get("companyCode"),
            "day": data.get("day"),
            "materialized": data.get("materialized", False),
            "publishable": data.get("publishable", False),
            "blockingReasons": data.get("blockingReasons") or [],
            "pagination": data.get("pagination") or {},
            "catalogCoverage": data.get("catalogCoverage") or {},
            "classificationCoverage": data.get("classificationCoverage") or {},
            "batches": batch_summary,
        }
