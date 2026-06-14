"""F08.2 — Retenção de snapshots financeiros (30 dias, preserva ativo e lineage único)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.services.financial_snapshot_config import get_financial_snapshot_config
from src.services.financial_snapshot_service import FINANCIAL_DIR

REMOVED_LOG = FINANCIAL_DIR / "_retention_removed.jsonl"


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00").split("+")[0])
    except ValueError:
        return None


def _has_lineage(payload: dict[str, Any]) -> bool:
    kind = str(payload.get("kind") or "")
    data = payload.get("data") or {}
    if kind == "financial_overview" and isinstance(data, dict) and data.get("postos"):
        return True
    rows = data.get("data") if isinstance(data, dict) else []
    if not isinstance(rows, list):
        return False
    return any(row.get("lineagePath") or row.get("rastreabilidadeOk") for row in rows)


class FinancialSnapshotRetentionService:
    def __init__(self, directory: Path = FINANCIAL_DIR) -> None:
        self._dir = directory
        self._active_snapshot_key: str | None = None
        self._removed_history: list[dict[str, Any]] = []

    def set_active_snapshot_key(self, key: str | None) -> None:
        self._active_snapshot_key = key

    def _iter_snapshots(self) -> list[tuple[Path, dict[str, Any]]]:
        items: list[tuple[Path, dict[str, Any]]] = []
        if not self._dir.is_dir():
            return items
        for path in sorted(self._dir.glob("financial_*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                items.append((path, payload))
        return items

    def _is_protected(self, path: Path, payload: dict[str, Any], *, lineage_counts: dict[str, int]) -> tuple[bool, str | None]:
        key = str(payload.get("key") or "")
        kind = str(payload.get("kind") or "")
        if self._active_snapshot_key and key == self._active_snapshot_key:
            return True, "active_snapshot"
        lineage_key = f"{kind}:{key}"
        if _has_lineage(payload) and lineage_counts.get(lineage_key, 0) <= 1:
            return True, "unique_lineage"
        if self._active_snapshot_key and self._active_snapshot_key in path.name:
            return True, "active_file"
        return False, None

    def list_expired_snapshots(self, retention_days: int | None = None) -> list[dict[str, Any]]:
        cfg = get_financial_snapshot_config()
        days = retention_days if retention_days is not None else cfg.retention_days
        cutoff = datetime.now() - timedelta(days=days)
        expired: list[dict[str, Any]] = []
        items = self._iter_snapshots()
        lineage_counts: dict[str, int] = {}
        for _, payload in items:
            if _has_lineage(payload):
                lk = f"{payload.get('kind')}:{payload.get('key')}"
                lineage_counts[lk] = lineage_counts.get(lk, 0) + 1

        for path, payload in items:
            ts = _parse_ts(payload.get("lastUpdated"))
            if ts is None or ts >= cutoff:
                continue
            protected, reason = self._is_protected(path, payload, lineage_counts=lineage_counts)
            expired.append(
                {
                    "file": path.name,
                    "snapshotType": payload.get("kind"),
                    "snapshotKey": payload.get("key"),
                    "lastUpdated": payload.get("lastUpdated"),
                    "protected": protected,
                    "protectReason": reason,
                    "lineagePresent": _has_lineage(payload),
                }
            )
        return expired

    def apply_retention(self, retention_days: int | None = None) -> dict[str, Any]:
        expired = self.list_expired_snapshots(retention_days)
        removed: list[dict[str, Any]] = []
        kept = 0
        for item in expired:
            if item.get("protected"):
                kept += 1
                continue
            path = self._dir / str(item.get("file"))
            if path.exists():
                path.unlink(missing_ok=True)
                record = {
                    "removedAt": datetime.now().isoformat(timespec="seconds"),
                    "file": item.get("file"),
                    "snapshotType": item.get("snapshotType"),
                    "snapshotKey": item.get("snapshotKey"),
                    "lastUpdated": item.get("lastUpdated"),
                }
                removed.append(record)
                self._log_removed(record)

        all_files = len(self._iter_snapshots())
        return {
            "removed": [r["file"] for r in removed],
            "removedDetails": removed,
            "removedCount": len(removed),
            "keptProtected": kept,
            "totalFiles": all_files,
            "retentionDays": retention_days or get_financial_snapshot_config().retention_days,
        }

    def list_removed_history(self, limit: int = 20) -> list[dict[str, Any]]:
        if self._removed_history:
            return self._removed_history[-limit:]
        if not REMOVED_LOG.exists():
            return []
        rows: list[dict[str, Any]] = []
        try:
            for line in REMOVED_LOG.read_text(encoding="utf-8").splitlines()[-limit:]:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError:
            return []
        return rows

    def _log_removed(self, record: dict[str, Any]) -> None:
        self._removed_history.append(record)
        REMOVED_LOG.parent.mkdir(parents=True, exist_ok=True)
        with REMOVED_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def purge_expired(self, retention_days: int | None = None) -> dict[str, Any]:
        return self.apply_retention(retention_days)


_retention: FinancialSnapshotRetentionService | None = None


def get_retention_service() -> FinancialSnapshotRetentionService:
    global _retention
    if _retention is None:
        _retention = FinancialSnapshotRetentionService()
    return _retention
