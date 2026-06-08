from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from src.gateway.webposto_client import WebPostoClient
from src.services.analytics_multiselect import build_finance_center_filters
from src.services.corporate_cash_flow_service import CorporateCashFlowService
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.network_financial_overview_service import NetworkFinancialOverviewService
from src.services.snapshot_store import SnapshotStore

CASH_FLOW_SNAPSHOT_TTL_SECONDS = 5 * 60


class CashFlowSnapshotService:
    def __init__(
        self,
        cash_flow: CorporateCashFlowService,
        output_dir: str = "snapshots/cash_flow",
        ttl_seconds: float = CASH_FLOW_SNAPSHOT_TTL_SECONDS,
    ) -> None:
        self._flow = cash_flow
        self._store = SnapshotStore(output_dir, ttl_seconds)
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    @staticmethod
    def _key(data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        suffix = empresa_snapshot_suffix(empresa_codigo)
        return f"cashflow:all:{data_inicial}:{data_final}:{suffix}"

    def get_snapshot(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        key = self._key(data_inicial, data_final, empresa_codigo)
        stored = self._store.load(key)
        if stored:
            return {
                "fromSnapshot": True,
                "lastUpdated": stored.get("lastUpdated"),
                "flow": stored.get("flow"),
            }
        return {"fromSnapshot": False, "lastUpdated": None, "flow": None}

    async def collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        filters = build_finance_center_filters(data_inicial, data_final, empresa_codigo)
        resp = await self._flow.build(filters, empresa_codigo)
        flow = resp.data if resp.success else None
        payload = {
            "lastUpdated": datetime.now().isoformat(timespec="seconds"),
            "flow": flow,
            "snapshotKey": self._key(data_inicial, data_final, empresa_codigo),
        }
        if flow:
            self._store.save(self._key(data_inicial, data_final, empresa_codigo), payload)
        return payload

    async def refresh_background(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> None:
        key = self._key(data_inicial, data_final, empresa_codigo)
        async with self._lock:
            if key in self._running:
                return
            self._running.add(key)
        try:
            await self.collect(data_inicial, data_final, empresa_codigo)
        finally:
            async with self._lock:
                self._running.discard(key)
