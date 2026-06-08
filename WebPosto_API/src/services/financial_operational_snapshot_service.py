from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from src.services.executive_snapshot_service import build_snapshot_key
from src.services.multiselect_utils import parse_empresa_codigos
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService
from src.services.snapshot_store import SnapshotStore

FINANCIAL_SNAPSHOT_TTL_SECONDS = 5 * 60


def _build_filters(
    data_inicial: str,
    data_final: str,
    empresa_codigo: str | int | None,
    centro_custo: str | None = None,
    tipo_despesa: str | None = None,
) -> FinancialOverviewFilters:
    codes = parse_empresa_codigos(empresa_codigo)
    if len(codes) == 1:
        return FinancialOverviewFilters(
            data_inicial=data_inicial,
            data_final=data_final,
            empresa_codigo=codes[0],
            centro_custo=centro_custo,
            tipo_despesa=tipo_despesa,
        )
    if len(codes) > 1:
        return FinancialOverviewFilters(
            data_inicial=data_inicial,
            data_final=data_final,
            empresa_codigos=tuple(codes),
            centro_custo=centro_custo,
            tipo_despesa=tipo_despesa,
        )
    return FinancialOverviewFilters(
        data_inicial=data_inicial,
        data_final=data_final,
        centro_custo=centro_custo,
        tipo_despesa=tipo_despesa,
    )


class FinancialOperationalSnapshotService:
    def __init__(
        self,
        overview: NetworkFinancialOverviewService,
        output_dir: str = "snapshots/financial",
        ttl_seconds: float = FINANCIAL_SNAPSHOT_TTL_SECONDS,
    ) -> None:
        self._overview = overview
        self._store = SnapshotStore(output_dir, ttl_seconds)
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    def get_snapshot(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        centro_custo: str | None = None,
        tipo_despesa: str | None = None,
    ) -> dict[str, Any]:
        key = build_snapshot_key(data_inicial, data_final, empresa_codigo)
        stored = self._store.load(key)
        if stored:
            return {
                "fromSnapshot": True,
                "lastUpdated": stored.get("lastUpdated"),
                "overview": stored.get("overview"),
                "expenses": stored.get("expenses"),
                "accounts": stored.get("accounts"),
                "warnings": stored.get("warnings") or [],
            }
        return {
            "fromSnapshot": False,
            "lastUpdated": None,
            "overview": None,
            "expenses": None,
            "accounts": None,
            "warnings": [],
        }

    async def collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        centro_custo: str | None = None,
        tipo_despesa: str | None = None,
    ) -> dict[str, Any]:
        warnings: list[str] = []
        filters = _build_filters(data_inicial, data_final, empresa_codigo, centro_custo, tipo_despesa)

        overview_resp = await self._overview.get_financial_overview_only(filters)
        overview = overview_resp.data if overview_resp.success else None
        if not overview_resp.success:
            warnings.append(f"overview: {overview_resp.error or 'falha'}")

        expenses_resp = await self._overview.get_financial_expenses(filters, page=1, limit=500)
        expenses = expenses_resp.data if expenses_resp.success else None
        if not expenses_resp.success:
            warnings.append(f"expenses: {expenses_resp.error or 'falha'}")

        accounts_resp = await self._overview.get_accounts_payable(filters, page=1, limit=500)
        accounts = accounts_resp.data if accounts_resp.success else None
        if not accounts_resp.success:
            warnings.append(f"accounts: {accounts_resp.error or 'falha'}")

        return {
            "lastUpdated": datetime.now().isoformat(timespec="seconds"),
            "overview": overview,
            "expenses": expenses,
            "accounts": accounts,
            "warnings": warnings,
        }

    async def refresh(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        centro_custo: str | None = None,
        tipo_despesa: str | None = None,
    ) -> dict[str, Any]:
        key = build_snapshot_key(data_inicial, data_final, empresa_codigo)
        async with self._lock:
            if key in self._running:
                return {"status": "already_running", "key": key}
            self._running.add(key)
        try:
            collected = await self.collect(
                data_inicial, data_final, empresa_codigo, centro_custo, tipo_despesa
            )
            has_data = any(collected.get(field) is not None for field in ("overview", "expenses", "accounts"))
            if has_data:
                self._store.save(key, collected)
            return {
                "status": "completed",
                "key": key,
                "lastUpdated": collected.get("lastUpdated"),
                "warnings": collected.get("warnings") or [],
            }
        finally:
            async with self._lock:
                self._running.discard(key)

    def start_refresh_background(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        centro_custo: str | None = None,
        tipo_despesa: str | None = None,
    ) -> dict[str, Any]:
        key = build_snapshot_key(data_inicial, data_final, empresa_codigo)
        if key in self._running:
            return {"status": "already_running", "key": key}

        async def _runner() -> None:
            await self.refresh(
                data_inicial, data_final, empresa_codigo, centro_custo, tipo_despesa
            )

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_runner())
            return {"status": "started", "key": key}
        except RuntimeError:
            return {"status": "already_running", "key": key}
