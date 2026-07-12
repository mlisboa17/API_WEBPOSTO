"""F08.0 / RT-02 — Snapshot-first com fallback live budgetado."""
from __future__ import annotations

import asyncio
from typing import Any

from src.gateway.webposto_client import WebPostoClient
from src.infrastructure.config.settings import settings
from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse
from src.services.financial_snapshot_service import FinancialSnapshotService
from src.services.financial_snapshot_health_service import FinancialSnapshotHealthService
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService

BANNER_SNAPSHOT = "Dados exibidos a partir do snapshot homologado"
BANNER_DEGRADED = "Modo degradado — snapshot homologado indisponível para o período"


class FinancialResilienceService:
    def __init__(
        self,
        overview: NetworkFinancialOverviewService | None = None,
        snapshots: FinancialSnapshotService | None = None,
        client: WebPostoClient | None = None,
    ) -> None:
        self._client = client or WebPostoClient()
        self._overview = overview or NetworkFinancialOverviewService(self._client)
        self._snapshots = snapshots or FinancialSnapshotService()
        self._health = FinancialSnapshotHealthService(self._snapshots)

    @staticmethod
    def _empresa_for_key(filters: FinancialOverviewFilters) -> str | int | None:
        if filters.empresa_codigos:
            return ",".join(str(c) for c in filters.empresa_codigos)
        return filters.empresa_codigo

    def _circuit_for_financial(self) -> str:
        return self._client.breaker.get_status("despesas_financeiro_rede")

    def _resilience_meta(
        self,
        *,
        source: str,
        key: str,
        mode: str,
        reason: str,
        live_attempted: bool = False,
        last_updated: str | None = None,
        banner: str | None = None,
        live_error: Any = None,
        snapshot_kind: str | None = None,
        snap_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        meta = {
            "source": source,
            "mode": mode,
            "reason": reason,
            "liveAttempted": live_attempted,
            "snapshotKey": key,
            "lastUpdated": last_updated,
            "banner": banner,
            "circuitStatus": self._circuit_for_financial(),
            "liveError": live_error.to_dict() if hasattr(live_error, "to_dict") else live_error,
        }
        if snapshot_kind and snap_payload:
            health = self._health.assess_kind_payload(snapshot_kind, snap_payload)
            if health:
                meta["health"] = health
                meta["dataOrigin"] = health.get("source") or source
                meta["snapshotAgeHours"] = health.get("snapshotAgeHours")
                meta["healthStatus"] = health.get("healthStatus")
                meta["confidenceLevel"] = health.get("confidenceLevel")
        elif source == "live":
            meta["dataOrigin"] = "live"
            meta["healthStatus"] = "HEALTHY"
            meta["confidenceLevel"] = "ALTA"
        return meta

    @staticmethod
    def _schedule_recovery(filters: FinancialOverviewFilters, key: str) -> None:
        try:
            from src.services.financial_auto_recovery_service import get_financial_auto_recovery

            empresa = None
            if filters.empresa_codigos:
                empresa = ",".join(str(c) for c in filters.empresa_codigos)
            else:
                empresa = filters.empresa_codigo
            get_financial_auto_recovery().register_failure(
                snapshot_key=key,
                data_inicial=filters.data_inicial,
                data_final=filters.data_final,
                empresa_codigo=empresa,
            )
        except Exception:
            return

    def _snapshot_overview_response(
        self,
        *,
        filters: FinancialOverviewFilters,
        key: str,
        snap: dict[str, Any],
        reason: str,
        live_attempted: bool,
        live_error: Any = None,
    ) -> dict[str, Any]:
        return {
            "success": True,
            "source": "snapshot",
            "data": snap["data"],
            "error": None,
            "resilience": self._resilience_meta(
                source="snapshot",
                mode="snapshot_first",
                reason=reason,
                live_attempted=live_attempted,
                key=key,
                last_updated=snap.get("lastUpdated"),
                banner=BANNER_SNAPSHOT,
                live_error=live_error,
                snapshot_kind="financial_overview",
                snap_payload=snap,
            ),
        }

    async def get_financial_overview(self, filters: FinancialOverviewFilters) -> dict[str, Any]:
        data_inicial, data_final = self._period_bounds(filters)
        key = self._snapshots.build_key(data_inicial, data_final, self._empresa_for_key(filters))
        self._snapshots.ensure_homologated(data_inicial, data_final, self._empresa_for_key(filters))

        exp_snap = self._snapshots.load_kind("financial_expenses", key)
        if exp_snap and exp_snap.get("data"):
            filtered = self._filtered_expense_snap(exp_snap, filters)
            if filtered:
                overview_data = self._snapshots.build_overview_from_expense_rows(filtered["data"].get("data") or [])
                return self._snapshot_overview_response(
                    filters=filters,
                    key=key,
                    snap={"data": overview_data, "lastUpdated": filtered.get("lastUpdated")},
                    reason="homologated_snapshot",
                    live_attempted=False,
                )

        live = await self._live_with_budget(
            self._overview.get_financial_overview_only(filters),
            endpoint="financial_overview",
        )
        if live.success and live.data:
            self._snapshots.save_kind("financial_overview", key, live.data, source="live")
            body = live.to_dict()
            body["source"] = "live"
            body["resilience"] = self._resilience_meta(
                source="live",
                mode="live",
                reason="ok",
                live_attempted=True,
                key=key,
                banner=None,
            )
            return body

        if exp_snap and exp_snap.get("data"):
            filtered_rows = self._snapshots.filter_rows_by_date(
                exp_snap["data"].get("data") or [],
                data_inicial,
                data_final,
            )
            if filtered_rows:
                overview_data = self._snapshots.build_overview_from_expense_rows(filtered_rows)
                self._schedule_recovery(filters, key)
                return self._snapshot_overview_response(
                    filters=filters,
                    key=key,
                    snap={"data": overview_data, "lastUpdated": exp_snap.get("lastUpdated")},
                    reason=self._failure_reason(live.error),
                    live_attempted=True,
                    live_error=live.error,
                )

        return {
            "success": True,
            "source": "degraded",
            "data": {
                "postos": [],
                "consolidado": {"total_despesas": "0", "total_a_pagar": "0", "synthetic": True},
            },
            "error": None,
            "resilience": self._resilience_meta(
                source="degraded",
                mode="degraded",
                reason=self._failure_reason(live.error),
                live_attempted=True,
                key=key,
                banner=BANNER_DEGRADED,
                live_error=live.error,
            ),
        }

    @staticmethod
    def _failure_reason(error: WebPostoError | None) -> str:
        if error is None:
            return "live_error"
        if str(error.type or "").upper() == "LIVE_TIMEOUT":
            return "live_timeout"
        return "live_error"

    async def _live_with_budget(self, coro, *, endpoint: str) -> WebPostoResponse:
        budget = settings.financial_live_budget_seconds
        task = asyncio.create_task(coro)
        try:
            return await asyncio.wait_for(task, timeout=budget)
        except asyncio.TimeoutError:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return WebPostoResponse.fail(
                WebPostoError(
                    endpoint=endpoint,
                    type="LIVE_TIMEOUT",
                    message=f"Consulta live excedeu o orçamento de {budget}s",
                )
            )

    @staticmethod
    def _period_bounds(filters: FinancialOverviewFilters) -> tuple[str, str]:
        return FinancialSnapshotService.normalize_period(filters.data_inicial, filters.data_final)

    def _filtered_expense_snap(
        self,
        snap: dict[str, Any],
        filters: FinancialOverviewFilters,
    ) -> dict[str, Any] | None:
        payload = snap.get("data")
        if not isinstance(payload, dict):
            return None
        rows = payload.get("data") or []
        if not isinstance(rows, list):
            return None
        filtered_rows = self._snapshots.filter_rows_by_date(
            rows,
            filters.data_inicial,
            filters.data_final,
        )
        if not filtered_rows:
            return None
        filtered_payload = dict(payload)
        filtered_payload["data"] = filtered_rows
        filtered_payload["total"] = len(filtered_rows)
        return {"data": filtered_payload, "lastUpdated": snap.get("lastUpdated")}

    def _paginate_expenses(self, snap: dict[str, Any], *, page: int, limit: int) -> dict[str, Any]:
        data = dict(snap["data"])
        rows = data.get("data") or []
        start = max(page - 1, 0) * limit
        page_rows = rows[start : start + limit]
        data["page"] = page
        data["limit"] = limit
        data["total"] = len(rows)
        data["data"] = page_rows
        return data

    async def get_financial_expenses(
        self,
        filters: FinancialOverviewFilters,
        page: int = 1,
        limit: int = 50,
    ) -> dict[str, Any]:
        data_inicial, data_final = self._period_bounds(filters)
        key = self._snapshots.build_key(data_inicial, data_final, self._empresa_for_key(filters))
        self._snapshots.ensure_homologated(data_inicial, data_final, self._empresa_for_key(filters))
        snap = self._snapshots.load_kind("financial_expenses", key)
        if snap and snap.get("data"):
            filtered = self._filtered_expense_snap(snap, filters)
            if filtered:
                data = self._paginate_expenses(filtered, page=page, limit=limit)
                return {
                    "success": True,
                    "source": "snapshot",
                    "data": data,
                    "error": None,
                    "resilience": self._resilience_meta(
                        source="snapshot",
                        mode="snapshot_first",
                        reason="homologated_snapshot",
                        live_attempted=False,
                        key=key,
                        last_updated=snap.get("lastUpdated"),
                        banner=BANNER_SNAPSHOT,
                        snapshot_kind="financial_expenses",
                        snap_payload=snap,
                    ),
                }

        live = await self._live_with_budget(
            self._overview.get_financial_expenses(filters, page=page, limit=limit),
            endpoint="financial_expenses",
        )
        if live.success and live.data:
            self._snapshots.save_kind("financial_expenses", key, live.data, source="live")
            body = live.to_dict()
            body["source"] = "live"
            body["resilience"] = self._resilience_meta(
                source="live",
                mode="live",
                reason="ok",
                live_attempted=True,
                key=key,
                banner=None,
            )
            return body

        snap = self._snapshots.load_kind("financial_expenses", key)
        if snap and snap.get("data"):
            filtered = self._filtered_expense_snap(snap, filters)
            if filtered:
                data = self._paginate_expenses(filtered, page=page, limit=limit)
                self._schedule_recovery(filters, key)
                return {
                    "success": True,
                    "source": "snapshot",
                    "data": data,
                    "error": None,
                    "resilience": self._resilience_meta(
                        source="snapshot",
                        mode="snapshot_fallback",
                        reason=self._failure_reason(live.error),
                        live_attempted=True,
                        key=key,
                        last_updated=snap.get("lastUpdated"),
                        banner=BANNER_SNAPSHOT,
                        live_error=live.error,
                        snapshot_kind="financial_expenses",
                        snap_payload=snap,
                    ),
                }

        return {
            "success": True,
            "source": "degraded",
            "data": {"page": page, "limit": limit, "total": 0, "data": []},
            "error": None,
            "resilience": self._resilience_meta(
                source="degraded",
                mode="degraded",
                reason=self._failure_reason(live.error),
                live_attempted=True,
                key=key,
                banner=BANNER_DEGRADED,
                live_error=live.error,
            ),
        }

    def _paginate_list_snap(self, snap: dict[str, Any], *, page: int, limit: int) -> dict[str, Any]:
        data = dict(snap["data"])
        rows = data.get("data") or []
        start = max(page - 1, 0) * limit
        page_rows = rows[start : start + limit]
        data["page"] = page
        data["limit"] = limit
        data["total"] = len(rows)
        data["data"] = page_rows
        return data

    async def _get_financial_paged(
        self,
        *,
        filters: FinancialOverviewFilters,
        kind: str,
        endpoint: str,
        live_fetch,
        page: int,
        limit: int,
    ) -> dict[str, Any]:
        data_inicial, data_final = self._period_bounds(filters)
        key = self._snapshots.build_key(data_inicial, data_final, self._empresa_for_key(filters))
        self._snapshots.ensure_homologated(data_inicial, data_final, self._empresa_for_key(filters))
        snap = self._snapshots.load_kind(kind, key)
        if snap and snap.get("data"):
            data = self._paginate_list_snap(snap, page=page, limit=limit)
            return {
                "success": True,
                "source": "snapshot",
                "data": data,
                "error": None,
                "resilience": self._resilience_meta(
                    source="snapshot",
                    mode="snapshot_first",
                    reason="homologated_snapshot",
                    live_attempted=False,
                    key=key,
                    last_updated=snap.get("lastUpdated"),
                    banner=BANNER_SNAPSHOT,
                    snapshot_kind=kind,
                    snap_payload=snap,
                ),
            }

        live = await self._live_with_budget(live_fetch, endpoint=endpoint)
        if live.success and live.data:
            self._snapshots.save_kind(kind, key, live.data, source="live")
            body = live.to_dict()
            body["source"] = "live"
            body["resilience"] = self._resilience_meta(
                source="live",
                mode="live",
                reason="ok",
                live_attempted=True,
                key=key,
                banner=None,
            )
            return body

        snap = self._snapshots.load_kind(kind, key)
        if snap and snap.get("data"):
            data = self._paginate_list_snap(snap, page=page, limit=limit)
            self._schedule_recovery(filters, key)
            return {
                "success": True,
                "source": "snapshot",
                "data": data,
                "error": None,
                "resilience": self._resilience_meta(
                    source="snapshot",
                    mode="snapshot_fallback",
                    reason=self._failure_reason(live.error),
                    live_attempted=True,
                    key=key,
                    last_updated=snap.get("lastUpdated"),
                    banner=BANNER_SNAPSHOT,
                    live_error=live.error,
                    snapshot_kind=kind,
                    snap_payload=snap,
                ),
            }

        return {
            "success": True,
            "source": "degraded",
            "data": {"page": page, "limit": limit, "total": 0, "data": [], "synthetic": True},
            "error": None,
            "resilience": self._resilience_meta(
                source="degraded",
                mode="degraded",
                reason=self._failure_reason(live.error),
                live_attempted=True,
                key=key,
                banner=BANNER_DEGRADED,
                live_error=live.error,
            ),
        }

    async def get_financial_accounts_payable(
        self,
        filters: FinancialOverviewFilters,
        page: int = 1,
        limit: int = 50,
    ) -> dict[str, Any]:
        return await self._get_financial_paged(
            filters=filters,
            kind="financial_payables",
            endpoint="financial_accounts_payable",
            live_fetch=self._overview.get_accounts_payable(filters, page=page, limit=limit),
            page=page,
            limit=limit,
        )

    async def get_financial_accounts_receivable(
        self,
        filters: FinancialOverviewFilters,
        page: int = 1,
        limit: int = 50,
    ) -> dict[str, Any]:
        return await self._get_financial_paged(
            filters=filters,
            kind="financial_receivables",
            endpoint="financial_accounts_receivable",
            live_fetch=self._overview.get_accounts_receivable(filters, page=page, limit=limit),
            page=page,
            limit=limit,
        )

    async def get_financial_companies(self) -> dict[str, Any]:
        live = await self._live_with_budget(self._overview.get_companies(), endpoint="financial_companies")
        if live.success and live.data:
            body = live.to_dict()
            body["source"] = "live"
            body["resilience"] = self._resilience_meta(
                source="live",
                mode="live",
                reason="ok",
                live_attempted=True,
                key="companies",
                banner=None,
            )
            return body

        return {
            "success": True,
            "source": "degraded",
            "data": {"data": [], "total": 0, "synthetic": True},
            "error": None,
            "resilience": self._resilience_meta(
                source="degraded",
                mode="degraded",
                reason=self._failure_reason(live.error),
                live_attempted=True,
                key="companies",
                banner=BANNER_DEGRADED,
                live_error=live.error,
            ),
        }
