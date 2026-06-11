"""Snapshot F03.2 — Expense Semantic Intelligence (TTL 300s, chave expenses:semantic)."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from src.core.config import load_core_config
from src.gateway.webposto_client import WebPostoClient
from src.services.expense_lineage_service import ExpenseLineageService
from src.services.expense_semantic_service import ExpenseSemanticService
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService
from src.services.snapshot_store import SnapshotStore

EXPENSE_SEMANTIC_SNAPSHOT_TTL_SECONDS = 300.0


class ExpenseSemanticSnapshotService:
    def __init__(
        self,
        overview: NetworkFinancialOverviewService | None = None,
        semantic: ExpenseSemanticService | None = None,
        lineage: ExpenseLineageService | None = None,
        output_dir: str = "snapshots/expense_semantic",
        ttl_seconds: float = EXPENSE_SEMANTIC_SNAPSHOT_TTL_SECONDS,
    ) -> None:
        cfg = load_core_config()
        client = WebPostoClient(cfg)
        self._overview = overview or NetworkFinancialOverviewService(client)
        self._semantic = semantic or ExpenseSemanticService()
        self._lineage = lineage or ExpenseLineageService()
        self._store = SnapshotStore(output_dir, ttl_seconds)
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    @staticmethod
    def _suffix(data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return f"{data_inicial}:{data_final}:{empresa_snapshot_suffix(empresa_codigo)}"

    @classmethod
    def key(cls, data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return f"expenses:semantic:{cls._suffix(data_inicial, data_final, empresa_codigo)}"

    def get_slice(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        key = self.key(data_inicial, data_final, empresa_codigo)
        stored, expired = self._store.load_stale(key)
        if stored:
            return {
                "fromSnapshot": True,
                "stale": expired,
                "hit": True,
                "lastUpdated": stored.get("lastUpdated"),
                "ttlSeconds": self._store.ttl_seconds,
                "data": stored.get("data"),
                "snapshotKey": key,
            }
        return {
            "fromSnapshot": False,
            "stale": True,
            "hit": False,
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
        payload = await self._semantic.build_semantic_payload(self._overview, filters, self._lineage)
        ts = datetime.now().isoformat(timespec="seconds")
        key = self.key(filters.data_inicial, filters.data_final, empresa_codigo)
        master = {
            "lastUpdated": ts,
            "payload": payload,
            "summary": payload.get("summary"),
            "cards": payload.get("cards"),
        }
        self._store.save(key, master)
        return master

    async def get_or_collect(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo: str | int | None = None,
    ) -> tuple[dict[str, Any] | None, bool, bool]:
        """Retorna (payload, stale, hit)."""
        key = self.key(filters.data_inicial, filters.data_final, empresa_codigo)
        stored, expired = self._store.load_stale(key)
        if stored and stored.get("payload"):
            if expired:
                asyncio.create_task(self._refresh(filters, empresa_codigo))
            return stored.get("payload"), expired, True
        collected = await self.collect(filters, empresa_codigo)
        return collected.get("payload"), False, False

    async def _refresh(self, filters: FinancialOverviewFilters, empresa_codigo: str | int | None) -> None:
        suffix = self._suffix(filters.data_inicial, filters.data_final, empresa_codigo)
        async with self._lock:
            if suffix in self._running:
                return
            self._running.add(suffix)
        try:
            await self.collect(filters, empresa_codigo)
        finally:
            async with self._lock:
                self._running.discard(suffix)
