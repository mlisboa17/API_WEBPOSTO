"""Snapshot isolado da DRE completa por empresa e período."""
from datetime import datetime, timezone
from typing import Any

from src.services.complete_departmental_dre_service import CompleteDepartmentalDreService
from src.services.snapshot_store import SnapshotStore


class CompleteDepartmentalDreSnapshotService:
    def __init__(self, service: CompleteDepartmentalDreService, output_dir: str = "snapshots/complete_departmental_dre", ttl_seconds: float = 900.0) -> None:
        self._service = service
        self._store = SnapshotStore(output_dir, ttl_seconds)

    @staticmethod
    def key(start: str, end: str, company_code: int | None) -> str:
        return f"complete-dre:v2:{start}:{end}:{company_code or 'network'}"

    async def get_or_collect(self, start: str, end: str, company_code: int | None = None) -> tuple[dict[str, Any], bool, bool]:
        key = self.key(start, end, company_code)
        stored, expired = self._store.load_stale(key)
        if stored and not expired:
            return stored["data"], False, True
        try:
            data = await self._service.build(start, end, company_code)
        except Exception:
            if stored:
                return stored["data"], True, True
            raise
        self._store.save(key, {"lastUpdated": datetime.now(timezone.utc).isoformat(), "data": data})
        return data, False, False
