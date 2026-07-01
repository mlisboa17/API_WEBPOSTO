"""F08.2 — Scheduler de snapshots financeiros (manual_tick + callable, sem loop no import)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from src.gateway.shared_client import get_webposto_client
from src.services.financial_snapshot_config import get_financial_snapshot_config
from src.services.financial_snapshot_execution_store import get_execution_store
from src.services.financial_snapshot_retention_service import get_retention_service
from src.services.financial_snapshot_service import FinancialSnapshotService, SNAPSHOT_KINDS
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService


def _record_count(kind: str, data: Any) -> int:
    if not isinstance(data, dict):
        return 0
    if kind == "financial_overview":
        return len(data.get("postos") or [])
    rows = data.get("data")
    if isinstance(rows, list):
        return len(rows)
    return int(data.get("total") or 0)


class FinancialSnapshotScheduler:
    def __init__(
        self,
        snapshots: FinancialSnapshotService | None = None,
        overview: NetworkFinancialOverviewService | None = None,
    ) -> None:
        client = get_webposto_client()
        self._snapshots = snapshots or FinancialSnapshotService()
        self._overview = overview or NetworkFinancialOverviewService(client)
        self._executions = get_execution_store()
        self._retention = get_retention_service()
        self._lock = asyncio.Lock()
        self._running = False
        self._last_run: datetime | None = None
        self._next_run_at: datetime | None = None
        self._last_result: dict[str, Any] | None = None
        self._last_period: tuple[str, str] | None = None
        self._active_snapshot_key: str | None = None

    def schedule_next_run(self, *, from_time: datetime | None = None) -> datetime | None:
        cfg = get_financial_snapshot_config()
        if not cfg.scheduler_enabled:
            self._next_run_at = None
            return None
        base = from_time or self._last_run or datetime.now()
        self._next_run_at = base + timedelta(seconds=cfg.refresh_interval_seconds)
        return self._next_run_at

    def get_scheduler_status(self) -> dict[str, Any]:
        cfg = get_financial_snapshot_config()
        if self._next_run_at is None and cfg.scheduler_enabled:
            self.schedule_next_run()
        status = "RUNNING" if self._running else ("ENABLED" if cfg.scheduler_enabled else "DISABLED")
        return {
            "status": status,
            "enabled": cfg.scheduler_enabled,
            "intervalSeconds": cfg.refresh_interval_seconds,
            "lastRunAt": self._last_run.isoformat(timespec="seconds") if self._last_run else None,
            "nextRunAt": self._next_run_at.isoformat(timespec="seconds") if self._next_run_at else None,
            "lastPeriod": {"dataInicial": self._last_period[0], "dataFinal": self._last_period[1]}
            if self._last_period
            else None,
            "activeSnapshotKey": self._active_snapshot_key,
            "lastResult": self._last_result,
            "snapshotKinds": list(cfg.snapshot_kinds),
        }

    async def run_due_jobs(self) -> dict[str, Any]:
        cfg = get_financial_snapshot_config()
        if not cfg.scheduler_enabled:
            return {"status": "disabled", "ran": False}
        now = datetime.now()
        if self._next_run_at is None:
            self.schedule_next_run()
        if self._next_run_at and now < self._next_run_at:
            return {"status": "waiting", "ran": False, "nextRunAt": self._next_run_at.isoformat(timespec="seconds")}
        result = await self.run_cycle(trigger="scheduler")
        self.schedule_next_run(from_time=datetime.now())
        return {"status": "executed", "ran": True, "result": result}

    async def refresh_kind(
        self,
        kind: str,
        filters: FinancialOverviewFilters,
        key: str,
        *,
        trigger: str = "scheduler",
    ) -> dict[str, Any]:
        started = datetime.now()
        execution_id = self._executions.start(kind, trigger=trigger)
        try:
            if kind == "financial_overview":
                resp = await self._overview.get_financial_overview_only(filters)
            elif kind == "financial_expenses":
                resp = await self._overview.get_financial_expenses(filters, page=1, limit=500)
            elif kind == "financial_receivables":
                resp = await self._overview.get_accounts_receivable(filters, page=1, limit=500)
            elif kind == "financial_payables":
                resp = await self._overview.get_accounts_payable(filters, page=1, limit=500)
            elif kind == "financial_sales":
                resp = await self._overview.get_sales(filters, page=1, limit=500)
            else:
                raise ValueError(f"kind desconhecido: {kind}")

            if resp.success and resp.data:
                self._snapshots.save_kind(kind, key, resp.data, source="scheduler")
                records = _record_count(kind, resp.data)
                self._executions.finish(
                    execution_id,
                    success=True,
                    started_at=started,
                    records=records,
                    source="live",
                    trigger_type=trigger,
                )
                return {"kind": kind, "success": True, "records": records, "source": "live"}

            error = str(resp.error or "live indisponível")
            self._snapshots.ensure_homologated(filters.data_inicial, filters.data_final, filters.empresa_codigo)
            snap = self._snapshots.load_kind(kind, key, allow_stale=True)
            if snap and snap.get("data") is not None:
                records = _record_count(kind, snap.get("data"))
                self._executions.finish(
                    execution_id,
                    success=True,
                    started_at=started,
                    records=records,
                    source="snapshot_fallback",
                    trigger_type=trigger,
                    error_type="live_unavailable",
                )
                return {"kind": kind, "success": True, "records": records, "source": "snapshot_fallback"}

            self._executions.finish(
                execution_id,
                success=False,
                started_at=started,
                error=error,
                trigger_type=trigger,
                error_type="refresh_failed",
            )
            return {"kind": kind, "success": False, "error": error}
        except Exception as exc:  # noqa: BLE001
            self._executions.finish(
                execution_id,
                success=False,
                started_at=started,
                error=str(exc),
                trigger_type=trigger,
                error_type="exception",
            )
            return {"kind": kind, "success": False, "error": str(exc)}

    async def run_cycle(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
        *,
        trigger: str = "scheduler",
    ) -> dict[str, Any]:
        cfg = get_financial_snapshot_config()
        if trigger == "scheduler" and not cfg.scheduler_enabled:
            return {"status": "disabled", "results": []}

        async with self._lock:
            if self._running:
                return {"status": "already_running"}
            self._running = True

        try:
            period = (
                data_inicial or cfg.default_period()[0],
                data_final or cfg.default_period()[1],
            )
            self._last_period = period
            filters = FinancialOverviewFilters(
                data_inicial=period[0],
                data_final=period[1],
                empresa_codigo=empresa_codigo,
            )
            key = self._snapshots.build_key(period[0], period[1], empresa_codigo)
            self._active_snapshot_key = key
            self._retention.set_active_snapshot_key(key)

            results: list[dict[str, Any]] = []
            for kind in SNAPSHOT_KINDS:
                results.append(await self.refresh_kind(kind, filters, key, trigger=trigger))

            retention = self._retention.apply_retention()
            success_count = sum(1 for r in results if r.get("success"))
            payload = {
                "status": "completed",
                "snapshotKey": key,
                "period": {"dataInicial": period[0], "dataFinal": period[1]},
                "kindsUpdated": success_count,
                "kindsTotal": len(SNAPSHOT_KINDS),
                "results": results,
                "retention": retention,
            }
            self._last_run = datetime.now()
            self._last_result = payload
            return payload
        finally:
            self._running = False


_scheduler: FinancialSnapshotScheduler | None = None


def get_financial_scheduler() -> FinancialSnapshotScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = FinancialSnapshotScheduler()
    return _scheduler
