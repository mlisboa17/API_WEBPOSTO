"""F08.0 — Live-first com fallback snapshot homologado."""
from __future__ import annotations

from typing import Any

from src.gateway.webposto_client import WebPostoClient
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
        last_updated: str | None = None,
        banner: str | None = None,
        live_error: Any = None,
        snapshot_kind: str | None = None,
        snap_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        meta = {
            "source": source,
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

    async def get_financial_overview(self, filters: FinancialOverviewFilters) -> dict[str, Any]:
        key = self._snapshots.build_key(filters.data_inicial, filters.data_final, self._empresa_for_key(filters))
        live = await self._overview.get_financial_overview_only(filters)
        if live.success and live.data:
            self._snapshots.save_kind("financial_overview", key, live.data, source="live")
            body = live.to_dict()
            body["resilience"] = self._resilience_meta(source="live", key=key, banner=None)
            return body

        self._snapshots.ensure_homologated(filters.data_inicial, filters.data_final, self._empresa_for_key(filters))
        snap = self._snapshots.load_kind("financial_overview", key)
        if snap:
            self._schedule_recovery(filters, key)
            return {
                "success": True,
                "data": snap["data"],
                "error": None,
                "resilience": self._resilience_meta(
                    source="snapshot",
                    key=key,
                    last_updated=snap.get("lastUpdated"),
                    banner=BANNER_SNAPSHOT,
                    live_error=live.error,
                    snapshot_kind="financial_overview",
                    snap_payload=snap,
                ),
            }

        return {
            "success": True,
            "data": {
                "postos": [],
                "consolidado": {"total_despesas": "0", "total_a_pagar": "0", "synthetic": True},
            },
            "error": None,
            "resilience": self._resilience_meta(
                source="degraded",
                key=key,
                banner=BANNER_DEGRADED,
                live_error=live.error,
            ),
        }

    async def get_financial_expenses(
        self,
        filters: FinancialOverviewFilters,
        page: int = 1,
        limit: int = 50,
    ) -> dict[str, Any]:
        key = self._snapshots.build_key(filters.data_inicial, filters.data_final, self._empresa_for_key(filters))
        live = await self._overview.get_financial_expenses(filters, page=page, limit=limit)
        if live.success and live.data:
            self._snapshots.save_kind("financial_expenses", key, live.data, source="live")
            body = live.to_dict()
            body["resilience"] = self._resilience_meta(source="live", key=key, banner=None)
            return body

        self._snapshots.ensure_homologated(filters.data_inicial, filters.data_final, self._empresa_for_key(filters))
        snap = self._snapshots.load_kind("financial_expenses", key)
        if snap and snap.get("data"):
            data = dict(snap["data"])
            rows = data.get("data") or []
            start = max(page - 1, 0) * limit
            page_rows = rows[start : start + limit]
            data["page"] = page
            data["limit"] = limit
            data["total"] = len(rows)
            data["data"] = page_rows
            self._schedule_recovery(filters, key)
            return {
                "success": True,
                "data": data,
                "error": None,
                "resilience": self._resilience_meta(
                    source="snapshot",
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
            "data": {"page": page, "limit": limit, "total": 0, "data": []},
            "error": None,
            "resilience": self._resilience_meta(
                source="degraded",
                key=key,
                banner=BANNER_DEGRADED,
                live_error=live.error,
            ),
        }
