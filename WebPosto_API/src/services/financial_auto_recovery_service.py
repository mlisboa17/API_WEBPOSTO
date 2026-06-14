"""F08.2 — Recuperação automática live após fallback snapshot (manual_tick + callable)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from src.gateway.shared_client import get_webposto_client
from src.services.financial_snapshot_config import get_financial_snapshot_config
from src.services.financial_snapshot_scheduler import FinancialSnapshotScheduler, get_financial_scheduler
from src.services.financial_snapshot_service import FinancialSnapshotService

FINANCIAL_ENDPOINT = "despesas_financeiro_rede"


@dataclass
class RecoveryJob:
    snapshot_key: str
    data_inicial: str
    data_final: str
    empresa_codigo: str | int | None = None
    scheduled_at: datetime = field(default_factory=datetime.now)
    attempts: int = 0
    last_attempt_at: datetime | None = None
    recovered_at: datetime | None = None
    last_error: str | None = None
    status: str = "PENDING"


class FinancialAutoRecoveryService:
    def __init__(
        self,
        scheduler: FinancialSnapshotScheduler | None = None,
        snapshots: FinancialSnapshotService | None = None,
    ) -> None:
        self._client = get_webposto_client()
        self._scheduler = scheduler or get_financial_scheduler()
        self._snapshots = snapshots or FinancialSnapshotService()
        self._jobs: dict[str, RecoveryJob] = {}
        self._lock = asyncio.Lock()
        self._last_cycle: datetime | None = None
        self._last_simulation: dict[str, Any] | None = None

    def register_failure(
        self,
        *,
        snapshot_key: str,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        cfg = get_financial_snapshot_config()
        if not cfg.auto_recovery_enabled:
            return {"registered": False, "reason": "disabled"}
        job = RecoveryJob(
            snapshot_key=snapshot_key,
            data_inicial=data_inicial,
            data_final=data_final,
            empresa_codigo=empresa_codigo,
        )
        self._jobs[snapshot_key] = job
        return {
            "registered": True,
            "snapshotKey": snapshot_key,
            "nextAttemptPolicy": f"a cada {cfg.recovery_interval_seconds}s",
        }

    def schedule(self, **kwargs: Any) -> dict[str, Any]:
        result = self.register_failure(**kwargs)
        result["scheduled"] = result.pop("registered", False)
        return result

    def get_recovery_status(self) -> dict[str, Any]:
        pending = [j for j in self._jobs.values() if j.status == "PENDING"]
        recovered = [j for j in self._jobs.values() if j.status == "RECOVERED"]
        cfg = get_financial_snapshot_config()
        circuit = self._client.breaker.get_status(FINANCIAL_ENDPOINT)
        return {
            "enabled": cfg.auto_recovery_enabled,
            "intervalSeconds": cfg.recovery_interval_seconds,
            "circuitStatus": circuit,
            "lastCycleAt": self._last_cycle.isoformat(timespec="seconds") if self._last_cycle else None,
            "pendingCount": len(pending),
            "recoveredCount": len(recovered),
            "jobs": [
                {
                    "snapshotKey": job.snapshot_key,
                    "status": job.status,
                    "attempts": job.attempts,
                    "scheduledAt": job.scheduled_at.isoformat(timespec="seconds"),
                    "lastAttemptAt": job.last_attempt_at.isoformat(timespec="seconds")
                    if job.last_attempt_at
                    else None,
                    "recoveredAt": job.recovered_at.isoformat(timespec="seconds") if job.recovered_at else None,
                    "lastError": job.last_error,
                    "period": {"dataInicial": job.data_inicial, "dataFinal": job.data_final},
                }
                for job in sorted(self._jobs.values(), key=lambda j: j.scheduled_at, reverse=True)[:20]
            ],
            "lastSimulation": self._last_simulation,
        }

    cockpit_state = get_recovery_status

    async def attempt_recovery(self, snapshot_key: str | None = None) -> dict[str, Any]:
        key = snapshot_key or next((j.snapshot_key for j in self._jobs.values() if j.status == "PENDING"), None)
        if not key or key not in self._jobs:
            return {"success": False, "reason": "job_not_found"}
        job = self._jobs[key]
        job.attempts += 1
        job.last_attempt_at = datetime.now()
        circuit = self._client.breaker.get_status(FINANCIAL_ENDPOINT)

        if circuit == "OPEN" and self._client.breaker.is_blocked(FINANCIAL_ENDPOINT):
            job.last_error = "circuit OPEN — aguardando HALF_OPEN/CLOSED"
            return {"success": False, "circuit": circuit, "reason": job.last_error, "snapshotKey": key}

        result = await self._scheduler.run_cycle(
            job.data_inicial,
            job.data_final,
            job.empresa_codigo,
            trigger="recovery",
        )
        live_hits = sum(
            1 for item in result.get("results") or [] if item.get("success") and item.get("source") == "live"
        )
        if live_hits > 0:
            job.status = "RECOVERED"
            job.recovered_at = datetime.now()
            job.last_error = None
            self._client.breaker.record_success(FINANCIAL_ENDPOINT)
            return {
                "success": True,
                "snapshotKey": key,
                "liveKinds": live_hits,
                "circuit": self._client.breaker.get_status(FINANCIAL_ENDPOINT),
            }

        job.last_error = "live ainda indisponível — snapshot mantido"
        return {"success": False, "snapshotKey": key, "circuit": self._client.breaker.get_status(FINANCIAL_ENDPOINT)}

    async def run_due_recoveries(self) -> dict[str, Any]:
        cfg = get_financial_snapshot_config()
        if not cfg.auto_recovery_enabled:
            return {"status": "disabled", "attempts": 0}
        self._last_cycle = datetime.now()
        outcomes: list[dict[str, Any]] = []
        async with self._lock:
            pending = [job for job in self._jobs.values() if job.status == "PENDING"]
        for job in pending:
            if job.last_attempt_at and datetime.now() - job.last_attempt_at < timedelta(
                seconds=cfg.recovery_interval_seconds
            ):
                continue
            outcomes.append(await self.attempt_recovery(job.snapshot_key))
        return {"status": "completed", "attempts": len(outcomes), "outcomes": outcomes}

    run_cycle = run_due_recoveries

    async def simulate(self, scenario: str) -> dict[str, Any]:
        from src.services.financial_health_alert_service import get_alert_service

        cfg = get_financial_snapshot_config()
        period = cfg.default_period()
        key = self._snapshots.build_key(period[0], period[1], None)
        report: dict[str, Any] = {"scenario": scenario, "steps": [], "alerts": []}

        if scenario == "circuit_open":
            self._client.breaker.block_endpoint(FINANCIAL_ENDPOINT, duration_seconds=120)
            report["steps"].append("circuit OPEN")
            cycle = await self._scheduler.run_cycle(period[0], period[1], trigger="simulation")
            report["steps"].append(f"UI snapshot fallback: {cycle.get('kindsUpdated')} kinds")
            self.register_failure(snapshot_key=key, data_inicial=period[0], data_final=period[1])
            report["steps"].append("recovery registrado")
            self._client.breaker.reset(FINANCIAL_ENDPOINT)
            report["steps"].append("circuit CLOSED")
            report["success"] = True
        elif scenario == "live_unavailable":
            self._client.breaker.block_endpoint(FINANCIAL_ENDPOINT, duration_seconds=3600)
            cycle = await self._scheduler.run_cycle(period[0], period[1], trigger="simulation")
            snap = self._snapshots.load_kind("financial_overview", key, allow_stale=True)
            report["steps"].append(f"snapshot assume: {'sim' if snap else 'nao'}")
            report["success"] = bool(snap)
            self._client.breaker.reset(FINANCIAL_ENDPOINT)
        elif scenario == "snapshot_expired":
            snap = self._snapshots.load_kind("financial_overview", key, allow_stale=True)
            report["steps"].append(f"allow_stale: {'sim' if snap else 'nao'}")
            ensured = self._snapshots.ensure_homologated(period[0], period[1], None)
            report["steps"].append(f"ensure_homologated: {len(ensured)} kinds")
            report["success"] = bool(snap) or len(ensured) > 0
        elif scenario == "health_warning":
            alerts = get_alert_service().generate(period[0], period[1])
            report["alerts"] = alerts
            report["steps"].append(f"alertas gerados: {len(alerts)}")
            report["success"] = any(a.get("severity") in {"WARNING", "INFO"} for a in alerts)
        elif scenario == "health_critical":
            alerts = get_alert_service().generate(period[0], period[1])
            report["alerts"] = alerts
            report["steps"].append(f"alertas gerados: {len(alerts)}")
            report["success"] = len(alerts) > 0
        else:
            report["success"] = False
            report["error"] = f"cenario desconhecido: {scenario}"

        self._last_simulation = report
        return report


_recovery: FinancialAutoRecoveryService | None = None


def get_financial_auto_recovery() -> FinancialAutoRecoveryService:
    global _recovery
    if _recovery is None:
        _recovery = FinancialAutoRecoveryService()
    return _recovery
