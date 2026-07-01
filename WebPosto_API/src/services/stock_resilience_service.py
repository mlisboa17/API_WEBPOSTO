"""RT-02 — /v1/stock live-first non-blocking com fallback snapshot (padrão P0 sales)."""
from __future__ import annotations

import asyncio
from time import monotonic
from typing import Any

from src.gateway.stock_circuit import (
    STOCK_GATE_ENDPOINT,
    record_stock_live_failure,
    stock_circuit_open,
    stock_circuit_status,
)
from src.gateway.webposto_client import WebPostoClient
from src.infrastructure.config.settings import settings
from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse
from src.services.financial_snapshot_service import FinancialSnapshotService
from src.services.financial_snapshot_health_service import FinancialSnapshotHealthService
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService

BANNER_SNAPSHOT = "Dados exibidos a partir do snapshot homologado"
BANNER_DEGRADED = "Modo degradado — snapshot homologado indisponível para o período"


class StockResilienceService:
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

    @staticmethod
    def _failure_reason(error: WebPostoError | None) -> str:
        if error is None:
            return "live_error"
        error_type = str(error.type or "").upper()
        if error_type == "LIVE_TIMEOUT":
            return "live_timeout"
        if error_type == "CIRCUIT_OPEN":
            return "circuit_open"
        return "live_error"

    def _resilience_meta(
        self,
        *,
        source: str,
        key: str,
        mode: str,
        reason: str,
        live_attempted: bool,
        last_updated: str | None = None,
        banner: str | None = None,
        live_error: Any = None,
        snapshot_kind: str | None = None,
        snap_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "source": source,
            "mode": mode,
            "reason": reason,
            "liveAttempted": live_attempted,
            "snapshotKey": key,
            "lastUpdated": last_updated,
            "banner": banner,
            "circuitStatus": stock_circuit_status(self._client),
            "stockGate": STOCK_GATE_ENDPOINT,
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

    async def _attempt_live(
        self,
        filters: FinancialOverviewFilters,
        page: int,
        limit: int,
        *,
        timeout_seconds: float,
    ) -> WebPostoResponse:
        task = asyncio.create_task(self._overview.get_stock(filters, page=page, limit=limit))
        try:
            return await asyncio.wait_for(task, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return WebPostoResponse.fail(
                WebPostoError(
                    endpoint="financial_stock",
                    type="LIVE_TIMEOUT",
                    message=f"Consulta live excedeu o orçamento de {timeout_seconds}s",
                )
            )

    def _paginate_snapshot(
        self,
        snap: dict[str, Any],
        *,
        page: int,
        limit: int,
    ) -> dict[str, Any]:
        data = dict(snap["data"])
        rows = data.get("data") or []
        start = max(page - 1, 0) * limit
        page_rows = rows[start : start + limit]
        data["page"] = page
        data["limit"] = limit
        data["total"] = len(rows)
        data["data"] = page_rows
        return data

    def _snapshot_response(
        self,
        *,
        filters: FinancialOverviewFilters,
        key: str,
        snap: dict[str, Any],
        page: int,
        limit: int,
        reason: str,
        live_attempted: bool,
        live_error: Any,
        mode: str = "snapshot_fallback",
    ) -> dict[str, Any]:
        data = self._paginate_snapshot(snap, page=page, limit=limit)
        self._schedule_recovery(filters, key)
        return {
            "success": True,
            "source": "snapshot",
            "degraded": False,
            "data": data,
            "error": None,
            "resilience": self._resilience_meta(
                source="snapshot",
                mode=mode,
                reason=reason,
                live_attempted=live_attempted,
                key=key,
                last_updated=snap.get("lastUpdated"),
                banner=BANNER_SNAPSHOT,
                live_error=live_error,
                snapshot_kind="financial_stock",
                snap_payload=snap,
            ),
        }

    def _degraded_response(
        self,
        *,
        key: str,
        page: int,
        limit: int,
        reason: str,
        live_attempted: bool,
        live_error: Any,
    ) -> dict[str, Any]:
        return {
            "success": False,
            "source": "degraded",
            "degraded": True,
            "data": {
                "page": page,
                "limit": limit,
                "total": 0,
                "data": [],
                "consolidado": {"total_estoque": "0", "total_tanques": 0},
                "synthetic": True,
            },
            "error": {
                "type": "STOCK_DEGRADED",
                "message": BANNER_DEGRADED,
            },
            "resilience": self._resilience_meta(
                source="degraded",
                mode="degraded",
                reason=reason,
                live_attempted=live_attempted,
                key=key,
                banner=BANNER_DEGRADED,
                live_error=live_error,
            ),
        }

    async def get_stock(
        self,
        filters: FinancialOverviewFilters,
        page: int = 1,
        limit: int = 50,
    ) -> dict[str, Any]:
        started = monotonic()
        key = self._snapshots.build_key(filters.data_inicial, filters.data_final, self._empresa_for_key(filters))
        snap = self._snapshots.load_kind("financial_stock", key)

        if snap and snap.get("data"):
            return self._snapshot_response(
                filters=filters,
                key=key,
                snap=snap,
                page=page,
                limit=limit,
                reason="homologated_snapshot",
                live_attempted=False,
                live_error=None,
                mode="snapshot_first",
            )

        if stock_circuit_open(self._client):
            if snap and snap.get("data"):
                return self._snapshot_response(
                    filters=filters,
                    key=key,
                    snap=snap,
                    page=page,
                    limit=limit,
                    reason="circuit_open",
                    live_attempted=False,
                    live_error=WebPostoError(
                        endpoint=STOCK_GATE_ENDPOINT,
                        type="CIRCUIT_OPEN",
                        message="Circuito stock aberto — usando snapshot",
                    ),
                )
            return self._degraded_response(
                key=key,
                page=page,
                limit=limit,
                reason="circuit_open",
                live_attempted=False,
                live_error=WebPostoError(
                    endpoint=STOCK_GATE_ENDPOINT,
                    type="CIRCUIT_OPEN",
                    message="Circuito stock aberto",
                ),
            )

        elapsed = monotonic() - started
        remaining = settings.stock_total_budget_seconds - elapsed
        live_timeout = min(settings.stock_live_timeout_seconds, max(0.5, remaining))

        live = await self._attempt_live(filters, page, limit, timeout_seconds=live_timeout)
        reason = self._failure_reason(live.error)

        if live.success and live.data:
            self._snapshots.save_kind("financial_stock", key, live.data, source="live")
            body = live.to_dict()
            body["source"] = "live"
            body["degraded"] = False
            body["resilience"] = self._resilience_meta(
                source="live",
                mode="live",
                reason="ok",
                live_attempted=True,
                key=key,
                banner=None,
            )
            return body

        if reason in {"live_timeout", "live_error"}:
            record_stock_live_failure(self._client, block_seconds=settings.circuit_breaker_timeout)

        snap = self._snapshots.load_kind("financial_stock", key)
        if snap and snap.get("data"):
            return self._snapshot_response(
                filters=filters,
                key=key,
                snap=snap,
                page=page,
                limit=limit,
                reason=reason,
                live_attempted=True,
                live_error=live.error,
            )

        return self._degraded_response(
            key=key,
            page=page,
            limit=limit,
            reason=reason,
            live_attempted=True,
            live_error=live.error,
        )
