"""F08.2 — Facade operacional (scheduler + recovery + alertas + audit)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from src.gateway.shared_client import get_webposto_client
from src.services.financial_auto_recovery_service import get_financial_auto_recovery
from src.services.financial_health_alert_service import get_alert_service
from src.services.financial_snapshot_config import get_financial_snapshot_config
from src.services.financial_snapshot_execution_store import get_execution_store
from src.services.financial_snapshot_retention_service import get_retention_service
from src.services.financial_snapshot_scheduler import get_financial_scheduler


class FinancialOperationsService:
    async def cockpit(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        cfg = get_financial_snapshot_config()
        period = (
            data_inicial or cfg.default_period()[0],
            data_final or cfg.default_period()[1],
        )
        scheduler = get_financial_scheduler()
        recovery = get_financial_auto_recovery()
        await scheduler.run_due_jobs()
        await recovery.run_due_recoveries()

        alerts = get_alert_service().generate(period[0], period[1], empresa_codigo)
        circuit = get_webposto_client().get_circuit_status()
        financial_circuit = circuit.get("endpoints", {}).get("despesas_financeiro_rede", "CLOSED")
        retention_removed = get_retention_service().list_removed_history(20)

        return {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "period": {"dataInicial": period[0], "dataFinal": period[1]},
            "config": {
                "schedulerEnabled": cfg.scheduler_enabled,
                "refreshIntervalSeconds": cfg.refresh_interval_seconds,
                "retentionDays": cfg.retention_days,
                "autoRecoveryEnabled": cfg.auto_recovery_enabled,
                "recoveryIntervalSeconds": cfg.recovery_interval_seconds,
                "snapshotKinds": list(cfg.snapshot_kinds),
            },
            "scheduler": scheduler.get_scheduler_status(),
            "recovery": recovery.get_recovery_status(),
            "circuitBreaker": {
                "financialEndpoint": "despesas_financeiro_rede",
                "status": financial_circuit,
                "summary": circuit.get("summary", {}).get("financial", {}),
            },
            "alerts": alerts,
            "alertCounts": get_alert_service().active_count(alerts),
            "executions": get_execution_store().list_recent(20),
            "retentionPolicyDays": cfg.retention_days,
            "retentionRemoved": retention_removed,
        }


_operations: FinancialOperationsService | None = None


def get_operations_service() -> FinancialOperationsService:
    global _operations
    if _operations is None:
        _operations = FinancialOperationsService()
    return _operations
