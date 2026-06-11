"""Snapshot F03.1-B — Expense Lineage (TTL 300s)."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from src.core.config import load_core_config
from src.gateway.webposto_client import WebPostoClient
from src.services.expense_lineage_service import ExpenseLineageService
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService
from src.services.snapshot_store import SnapshotStore

EXPENSE_LINEAGE_SNAPSHOT_TTL_SECONDS = 300.0


class ExpenseLineageSnapshotService:
    def __init__(
        self,
        overview: NetworkFinancialOverviewService | None = None,
        lineage: ExpenseLineageService | None = None,
        output_dir: str = "snapshots/expense_lineage",
        ttl_seconds: float = EXPENSE_LINEAGE_SNAPSHOT_TTL_SECONDS,
    ) -> None:
        cfg = load_core_config()
        client = WebPostoClient(cfg)
        self._overview = overview or NetworkFinancialOverviewService(client)
        self._lineage = lineage or ExpenseLineageService()
        self._store = SnapshotStore(output_dir, ttl_seconds)
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    @staticmethod
    def _suffix(data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return f"{data_inicial}:{data_final}:{empresa_snapshot_suffix(empresa_codigo)}"

    @classmethod
    def key(cls, domain: str, data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return f"expense:{domain}:{cls._suffix(data_inicial, data_final, empresa_codigo)}"

    def get_slice(
        self,
        domain: str,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        key = self.key(domain, data_inicial, data_final, empresa_codigo)
        stored, expired = self._store.load_stale(key)
        if stored:
            return {
                "fromSnapshot": True,
                "stale": expired,
                "lastUpdated": stored.get("lastUpdated"),
                "ttlSeconds": self._store.ttl_seconds,
                "data": stored.get("data"),
                "snapshotKey": key,
            }
        return {
            "fromSnapshot": False,
            "stale": True,
            "lastUpdated": None,
            "ttlSeconds": self._store.ttl_seconds,
            "data": None,
            "snapshotKey": key,
        }

    async def collect(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        payload = await self._lineage.build_lineage_payload(self._overview, filters)
        ts = datetime.now().isoformat(timespec="seconds")
        suffix_args = (filters.data_inicial, filters.data_final, empresa_codigo)
        summary = payload.get("summary") or {}
        rows = payload.get("rows") or []

        slices = {
            "lineage": {
                "rows": rows,
                "coveragePct": summary.get("coveragePct"),
                "totalRecords": summary.get("totalRecords"),
            },
            "sources": {
                "byOrigemReal": summary.get("byOrigemReal"),
                "pctFinanceiro": summary.get("pctFinanceiro"),
                "pctOperacional": summary.get("pctOperacional"),
            },
            "categories": {
                "byClassificacao": summary.get("byClassificacao"),
                "byEvento": summary.get("byEvento"),
                "topDescriptions": summary.get("topDescriptions", [])[:100],
            },
            "operators": summary.get("topOperators"),
            "pdvs": summary.get("topPdvs"),
        }
        for domain, data in slices.items():
            self._store.save(
                self.key(domain, *suffix_args),
                {"lastUpdated": ts, "data": data, "snapshotKey": self.key(domain, *suffix_args)},
            )
        master = {"lastUpdated": ts, "payload": payload, "summary": summary}
        self._store.save(f"expense:master:{self._suffix(*suffix_args)}", master)
        return master

    async def get_or_collect(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo: str | int | None = None,
    ) -> tuple[dict[str, Any] | None, bool]:
        master_key = f"expense:master:{self._suffix(filters.data_inicial, filters.data_final, empresa_codigo)}"
        stored, expired = self._store.load_stale(master_key)
        if stored and stored.get("payload"):
            if expired:
                asyncio.create_task(self._refresh(filters, empresa_codigo))
            return stored.get("payload"), expired
        collected = await self.collect(filters, empresa_codigo)
        return collected.get("payload"), False

    async def _refresh(self, filters: FinancialOverviewFilters, empresa_codigo: str | int | None) -> None:
        key = self._suffix(filters.data_inicial, filters.data_final, empresa_codigo)
        async with self._lock:
            if key in self._running:
                return
            self._running.add(key)
        try:
            await self.collect(filters, empresa_codigo)
        finally:
            async with self._lock:
                self._running.discard(key)
