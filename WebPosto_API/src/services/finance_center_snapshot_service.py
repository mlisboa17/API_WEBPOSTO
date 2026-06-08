from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.snapshot_store import SnapshotStore
from src.services.analytics_multiselect import build_finance_center_filters

FINANCE_CENTER_SNAPSHOT_TTL_SECONDS = 5 * 60


class FinanceCenterSnapshotService:
    def __init__(
        self,
        finance_center: CorporateFinanceCenterService,
        output_dir: str = "snapshots/finance_center",
        ttl_seconds: float = FINANCE_CENTER_SNAPSHOT_TTL_SECONDS,
    ) -> None:
        self._center = finance_center
        self._store = SnapshotStore(output_dir, ttl_seconds)
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    @staticmethod
    def _key(data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        suffix = empresa_snapshot_suffix(empresa_codigo)
        return f"finance:center:all:{data_inicial}:{data_final}:{suffix}"

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
                "center": stored.get("center"),
                "warnings": stored.get("warnings") or [],
            }
        return {
            "fromSnapshot": False,
            "lastUpdated": None,
            "center": None,
            "warnings": [],
        }

    async def collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        filters = build_finance_center_filters(data_inicial, data_final, empresa_codigo)
        summary_resp, expenses_resp, payables_resp, receivables_resp, bank_resp, cash_resp = await asyncio.gather(
            self._center.get_summary(filters, empresa_codigo),
            self._center.get_expenses(filters, empresa_codigo, page=1, limit=500),
            self._center.get_payables(filters, empresa_codigo, page=1, limit=500),
            self._center.get_receivables(filters, empresa_codigo, page=1, limit=500),
            self._center.get_bank_movements(filters, empresa_codigo, page=1, limit=500),
            self._center.get_cash(filters, empresa_codigo),
        )

        warnings: list[str] = []
        for name, resp in (
            ("summary", summary_resp),
            ("expenses", expenses_resp),
            ("payables", payables_resp),
            ("receivables", receivables_resp),
            ("bank", bank_resp),
            ("cash", cash_resp),
        ):
            if not resp.success:
                warnings.append(f"{name}: {resp.error}")

        center = {
            "summary": summary_resp.data if summary_resp.success else None,
            "expenses": expenses_resp.data if expenses_resp.success else None,
            "payables": payables_resp.data if payables_resp.success else None,
            "receivables": receivables_resp.data if receivables_resp.success else None,
            "bank": bank_resp.data if bank_resp.success else None,
            "cash": cash_resp.data if cash_resp.success else None,
        }
        if summary_resp.success and summary_resp.data:
            warnings.extend(summary_resp.data.get("warnings") or [])

        payload = {
            "lastUpdated": datetime.now().isoformat(timespec="seconds"),
            "center": center,
            "warnings": warnings,
            "snapshotKey": self._key(data_inicial, data_final, empresa_codigo),
        }
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
