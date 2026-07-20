"""Snapshot da conciliação financeira da Diretoria (TTL de 5 minutos)."""

from datetime import datetime, timezone
from typing import Any

from src.services.director_financial_reconciliation_pipeline import DirectorFinancialReconciliationPipeline
from src.services.snapshot_store import SnapshotStore


DIRECTOR_RECONCILIATION_TTL_SECONDS = 300.0


class DirectorFinancialReconciliationSnapshotService:
    def __init__(
        self,
        pipeline: DirectorFinancialReconciliationPipeline,
        output_dir: str = "snapshots/director_financial_reconciliation",
        ttl_seconds: float = DIRECTOR_RECONCILIATION_TTL_SECONDS,
    ) -> None:
        self._pipeline = pipeline
        self._store = SnapshotStore(output_dir, ttl_seconds)

    @staticmethod
    def key(start: str, end: str, company_code: int | None) -> str:
        return f"director-reconciliation:{start}:{end}:{company_code or 'network'}"

    async def get_or_collect(
        self, start: str, end: str, company_code: int | None = None
    ) -> tuple[dict[str, Any], bool, bool]:
        key = self.key(start, end, company_code)
        stored, expired = self._store.load_stale(key)
        if stored and not expired:
            return stored["data"], False, True
        try:
            data = await self._pipeline.build(start, end, company_code)
        except Exception:
            if stored:
                return stored["data"], True, True
            raise
        self._store.save(key, {
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "data": data,
        })
        return data, False, bool(stored)

    async def refresh(self, start: str, end: str, company_code: int | None = None) -> dict[str, Any]:
        data = await self._pipeline.build(start, end, company_code)
        key = self.key(start, end, company_code)
        self._store.save(key, {
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "data": data,
        })
        return data
