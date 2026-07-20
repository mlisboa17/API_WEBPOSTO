"""Snapshot D02 — Conferência Financeira (TTL 300s)."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from src.services.cash_reconciliation.cash_reconciliation_service import CashReconciliationService
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.snapshot_store import SnapshotStore

RECON_SNAPSHOT_TTL = 300.0


class CashReconciliationSnapshotService:
    def __init__(
        self,
        service: CashReconciliationService | None = None,
        output_dir: str = "snapshots/cash_reconciliation",
        ttl_seconds: float = RECON_SNAPSHOT_TTL,
    ) -> None:
        self._svc = service or CashReconciliationService()
        self._store = SnapshotStore(output_dir, ttl_seconds)
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    @classmethod
    def master_key(cls, data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return f"recon:summary:{data_inicial}:{data_final}:{empresa_snapshot_suffix(empresa_codigo)}"

    async def get_or_collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> tuple[dict[str, Any] | None, bool, bool]:
        key = self.master_key(data_inicial, data_final, empresa_codigo)
        stored, expired = self._store.load_stale(key)
        if stored and stored.get("payload"):
            return stored["payload"], expired, True

        async with self._lock:
            if key in self._running:
                stored2, expired2 = self._store.load_stale(key)
                if stored2 and stored2.get("payload"):
                    return stored2["payload"], expired2, True
            self._running.add(key)
        try:
            resp = await self._svc.build_summary(data_inicial, data_final, empresa_codigo)
            ts = datetime.now().isoformat(timespec="seconds")
            if not resp.success:
                return None, True, False
            master = {"lastUpdated": ts, "payload": resp.data, "snapshotKey": key}
            self._store.save(key, master)
            return resp.data, False, False
        finally:
            self._running.discard(key)
