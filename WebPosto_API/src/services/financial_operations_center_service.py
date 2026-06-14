"""F08.3 — Financial Operations Center (consolida F08.0/F08.1/F08.2 sem WebPosto live)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from src.gateway.shared_client import get_webposto_client
from src.services.financial_auto_recovery_service import get_financial_auto_recovery
from src.services.financial_health_alert_service import get_alert_service
from src.services.financial_snapshot_config import get_financial_snapshot_config
from src.services.financial_snapshot_execution_store import get_execution_store
from src.services.financial_snapshot_health_service import FinancialSnapshotHealthService
from src.services.financial_snapshot_retention_service import get_retention_service
from src.services.financial_snapshot_scheduler import get_financial_scheduler

FINANCIAL_ENDPOINT = "despesas_financeiro_rede"


def _score_scheduler(status: dict[str, Any]) -> float:
    raw = str(status.get("status") or "").upper()
    if raw in {"ENABLED", "RUNNING"}:
        return 100.0
    if raw == "DISABLED":
        return 40.0
    return 60.0


def _score_recovery(status: dict[str, Any]) -> float:
    if not status.get("enabled"):
        return 70.0
    pending = int(status.get("pendingCount") or 0)
    recovered = int(status.get("recoveredCount") or 0)
    if pending == 0:
        return 100.0
    if recovered > 0:
        return max(50.0, 100.0 - pending * 15)
    return max(20.0, 80.0 - pending * 20)


def _score_alerts(counts: dict[str, int]) -> float:
    critical = int(counts.get("CRITICAL") or 0)
    warning = int(counts.get("WARNING") or 0)
    if critical == 0 and warning == 0:
        return 100.0
    if critical == 0:
        return max(60.0, 100.0 - warning * 10)
    return max(0.0, 50.0 - critical * 15)


def _score_circuits(circuit: dict[str, Any]) -> float:
    status = str(circuit.get("status") or "CLOSED").upper()
    if status == "CLOSED":
        return 100.0
    if status == "HALF_OPEN":
        return 55.0
    return 20.0


def _classify_health_score(score: float) -> str:
    if score >= 90:
        return "EXCELENTE"
    if score >= 75:
        return "BOM"
    if score >= 50:
        return "ATENÇÃO"
    return "CRÍTICO"


def _compute_executive_health_score(
    *,
    snapshot_health_score: float,
    scheduler: dict[str, Any],
    recovery: dict[str, Any],
    alert_counts: dict[str, int],
    circuit: dict[str, Any],
) -> dict[str, Any]:
    components = {
        "snapshotHealth": round(snapshot_health_score * 0.30, 1),
        "scheduler": round(_score_scheduler(scheduler) * 0.20, 1),
        "recovery": round(_score_recovery(recovery) * 0.20, 1),
        "alerts": round(_score_alerts(alert_counts) * 0.15, 1),
        "circuits": round(_score_circuits(circuit) * 0.15, 1),
    }
    total = round(sum(components.values()), 1)
    return {
        "score": total,
        "classification": _classify_health_score(total),
        "components": components,
        "weights": {"snapshotHealth": 30, "scheduler": 20, "recovery": 20, "alerts": 15, "circuits": 15},
    }


def _timeline_from_sources(
    *,
    executions: list[dict[str, Any]],
    recovery: dict[str, Any],
    alerts: list[dict[str, Any]],
    retention_removed: list[dict[str, Any]],
    circuit: dict[str, Any],
    scheduler: dict[str, Any],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for ex in executions:
        ts = ex.get("finished_at") or ex.get("started_at")
        if not ts:
            continue
        kind = ex.get("snapshot_type") or "snapshot"
        success = ex.get("success")
        events.append(
            {
                "eventType": "SNAPSHOT_GENERATED" if success else "SNAPSHOT_FAILED",
                "timestamp": ts,
                "label": f"Snapshot {kind}",
                "detail": f"trigger={ex.get('trigger_type') or ex.get('trigger')} source={ex.get('source') or '—'}",
                "severity": "INFO" if success else "WARNING",
                "lineage": ex.get("lineage"),
                "origin": ex.get("source") or kind,
            }
        )

    for job in recovery.get("jobs") or []:
        ts = job.get("recoveredAt") or job.get("lastAttemptAt") or job.get("scheduledAt")
        if not ts:
            continue
        if job.get("status") == "RECOVERED":
            events.append(
                {
                    "eventType": "RECOVERY_SUCCEEDED",
                    "timestamp": ts,
                    "label": "Recovery concluído",
                    "detail": job.get("snapshotKey"),
                    "severity": "INFO",
                    "origin": "recovery",
                }
            )
        elif job.get("status") == "PENDING":
            events.append(
                {
                    "eventType": "RECOVERY_TRIGGERED",
                    "timestamp": job.get("scheduledAt") or ts,
                    "label": "Recovery agendado",
                    "detail": job.get("lastError") or job.get("snapshotKey"),
                    "severity": "WARNING",
                    "origin": "recovery",
                }
            )

    for alert in alerts:
        code = str(alert.get("code") or "")
        sev = str(alert.get("severity") or "INFO")
        if code in {"HEALTH_OK", "MONITORING_ACTIVE"}:
            continue
        event_type = "HEALTH_CRITICAL" if sev == "CRITICAL" else "HEALTH_WARNING"
        events.append(
            {
                "eventType": event_type,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "label": code,
                "detail": alert.get("message"),
                "severity": sev,
                "origin": alert.get("origin"),
            }
        )

    for row in retention_removed:
        events.append(
            {
                "eventType": "RETENTION_APPLIED",
                "timestamp": row.get("removedAt"),
                "label": "Retention aplicada",
                "detail": row.get("file") or row.get("snapshotType"),
                "severity": "INFO",
                "origin": "retention",
            }
        )

    circuit_status = str(circuit.get("status") or "CLOSED").upper()
    events.append(
        {
            "eventType": "CIRCUIT_OPEN" if circuit_status == "OPEN" else "CIRCUIT_CLOSED",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "label": f"Circuit {circuit_status}",
            "detail": FINANCIAL_ENDPOINT,
            "severity": "CRITICAL" if circuit_status == "OPEN" else "INFO",
            "origin": "circuit_breaker",
        }
    )

    if scheduler.get("lastRunAt"):
        events.append(
            {
                "eventType": "SCHEDULER_RUN",
                "timestamp": scheduler.get("lastRunAt"),
                "label": "Scheduler executado",
                "detail": f"next={scheduler.get('nextRunAt')}",
                "severity": "INFO",
                "origin": "scheduler",
            }
        )

    events.sort(key=lambda e: e.get("timestamp") or "", reverse=True)
    return events[:50]


class FinancialOperationsCenterService:
    def __init__(self) -> None:
        self._health = FinancialSnapshotHealthService()

    def _period(
        self,
        data_inicial: str | None,
        data_final: str | None,
    ) -> tuple[str, str]:
        cfg = get_financial_snapshot_config()
        return (
            data_inicial or cfg.default_period()[0],
            data_final or cfg.default_period()[1],
        )

    def _collect(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        period = self._period(data_inicial, data_final)
        cfg = get_financial_snapshot_config()

        scheduler = get_financial_scheduler().get_scheduler_status()
        recovery = get_financial_auto_recovery().get_recovery_status()
        assessment = self._health.assess_key(period[0], period[1], empresa_codigo)
        inventory = self._health.inventory()
        alerts = get_alert_service().generate(period[0], period[1], empresa_codigo)
        alert_counts = get_alert_service().active_count(alerts)
        executions = get_execution_store().list_recent(30)
        retention = get_retention_service()
        retention_removed = retention.list_removed_history(20)
        circuit_raw = get_webposto_client().get_circuit_status()
        circuit = {
            "financialEndpoint": FINANCIAL_ENDPOINT,
            "status": circuit_raw.get("endpoints", {}).get(FINANCIAL_ENDPOINT, "CLOSED"),
            "summary": circuit_raw.get("summary", {}).get("financial", {}),
            "endpoints": circuit_raw.get("endpoints", {}),
        }

        summary_block = assessment.get("summary") or {}
        snapshot_health_score = float(summary_block.get("averageHealthScore") or 0)
        executive_health = _compute_executive_health_score(
            snapshot_health_score=snapshot_health_score,
            scheduler=scheduler,
            recovery=recovery,
            alert_counts=alert_counts,
            circuit=circuit,
        )

        timeline = _timeline_from_sources(
            executions=executions,
            recovery=recovery,
            alerts=alerts,
            retention_removed=retention_removed,
            circuit=circuit,
            scheduler=scheduler,
        )

        return {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "period": {"dataInicial": period[0], "dataFinal": period[1]},
            "empresaCodigo": empresa_codigo,
            "executiveHealthScore": executive_health,
            "scheduler": scheduler,
            "recovery": recovery,
            "snapshotHealth": {
                "assessment": assessment,
                "inventoryTotal": len(inventory),
                "coverageComplete": summary_block.get("coverageComplete"),
                "overallStatus": summary_block.get("overallStatus"),
            },
            "alerts": alerts,
            "alertCounts": alert_counts,
            "retention": {
                "policyDays": cfg.retention_days,
                "removed": retention_removed,
                "expiredCandidates": len(retention.list_expired_snapshots()),
            },
            "circuitBreakers": circuit,
            "executions": executions,
            "timeline": timeline,
            "cards": {
                "financialHealthScore": executive_health,
                "snapshotCoverage": {
                    "complete": summary_block.get("coverageComplete"),
                    "gaps": summary_block.get("coverageGaps") or [],
                    "total": summary_block.get("totalSnapshots"),
                    "expected": summary_block.get("expectedSnapshots"),
                },
                "recoveryStatus": recovery,
                "schedulerStatus": scheduler,
                "activeAlerts": alert_counts,
                "lastExecution": scheduler.get("lastRunAt"),
                "nextExecution": scheduler.get("nextRunAt"),
                "circuitStatus": circuit.get("status"),
            },
        }

    def get_operations_summary(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        data = self._collect(data_inicial, data_final, empresa_codigo)
        return {
            "generatedAt": data["generatedAt"],
            "period": data["period"],
            "executiveHealthScore": data["executiveHealthScore"],
            "cards": data["cards"],
            "snapshotFirst": True,
            "liveOptional": True,
        }

    def get_operational_status(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        data = self._collect(data_inicial, data_final, empresa_codigo)
        return {
            "generatedAt": data["generatedAt"],
            "period": data["period"],
            "scheduler": data["scheduler"],
            "recovery": data["recovery"],
            "snapshotHealth": data["snapshotHealth"],
            "retention": data["retention"],
            "circuitBreakers": data["circuitBreakers"],
            "executiveHealthScore": data["executiveHealthScore"],
        }

    def get_operational_alerts(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        data = self._collect(data_inicial, data_final, empresa_codigo)
        return {
            "generatedAt": data["generatedAt"],
            "alerts": data["alerts"],
            "alertCounts": data["alertCounts"],
        }

    def get_executions(
        self,
        limit: int = 50,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        _ = self._collect(data_inicial, data_final, empresa_codigo)
        rows = get_execution_store().list_recent(limit)
        return {"rows": rows, "total": len(rows)}

    def get_timeline(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        data = self._collect(data_inicial, data_final, empresa_codigo)
        return {"events": data["timeline"], "total": len(data["timeline"])}

    def get_full_cockpit(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        return self._collect(data_inicial, data_final, empresa_codigo)

    def dw_row(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        data = self._collect(data_inicial, data_final, empresa_codigo)
        health = data["executiveHealthScore"]
        counts = data["alertCounts"]
        return {
            "execution_id": str(uuid.uuid4()),
            "generated_at": data["generatedAt"],
            "health_score": health.get("score"),
            "health_classification": health.get("classification"),
            "scheduler_status": data["scheduler"].get("status"),
            "recovery_status": "PENDING" if data["recovery"].get("pendingCount") else "OK",
            "alert_count": sum(counts.values()),
            "critical_alerts": counts.get("CRITICAL", 0),
            "snapshot_count": data["snapshotHealth"]["assessment"]["summary"].get("totalSnapshots"),
            "empresa_codigo": empresa_codigo,
            "period_start": data["period"]["dataInicial"],
            "period_end": data["period"]["dataFinal"],
            "lineage": True,
            "source": "operations_center",
        }


_center: FinancialOperationsCenterService | None = None


def get_operations_center_service() -> FinancialOperationsCenterService:
    global _center
    if _center is None:
        _center = FinancialOperationsCenterService()
    return _center
