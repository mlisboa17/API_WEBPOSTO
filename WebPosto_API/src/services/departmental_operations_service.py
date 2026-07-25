"""Sprint 8 — saúde operacional e rotina executiva departamental."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.core.management_scope import LICENSED_COMPANIES
from src.services.departmental_alert_service import DepartmentalAlertService
from src.services.departmental_fact_store import DepartmentalFactStore
from src.services.departmental_history_service import DepartmentalHistoryService


DEPARTMENTAL_ROLE_PERMISSIONS = {
    "PRESIDENCY": ("read", "export"),
    "DIRECTOR": ("read", "export", "acknowledge"),
    "AUDIT": ("read", "export", "acknowledge", "close"),
    "OPERATIONS": ("read", "materialize", "acknowledge"),
}


class DepartmentalOperationsService:
    def __init__(self, facts: DepartmentalFactStore | None = None, alerts: DepartmentalAlertService | None = None) -> None:
        self._facts = facts or DepartmentalFactStore()
        self._alerts = alerts or DepartmentalAlertService()

    def health(self, reference_day: str | None = None) -> dict[str, Any]:
        day = reference_day or date.today().isoformat()
        companies = []
        for company in LICENSED_COMPANIES:
            available = self._facts.list_days(company.empresa_codigo)
            summary = self._facts.quality_summary(company.empresa_codigo, day)
            companies.append({
                "companyCode": company.empresa_codigo,
                "companyName": company.nome,
                "referenceDayAvailable": summary is not None,
                "latestMaterializedDay": available[-1] if available else None,
                "publishable": summary.get("publishable") if summary else False,
                "blockingReasons": summary.get("blockingReasons") if summary else ["MATERIALIZATION_MISSING"],
            })
        return {
            "checkedAt": datetime.now(timezone.utc).isoformat(),
            "referenceDay": day,
            "status": (
                "HEALTHY"
                if all(item["referenceDayAvailable"] and item["publishable"] for item in companies)
                else "DEGRADED"
            ),
            "companies": companies,
            "credentials": {"configuredCompanies": len(LICENSED_COMPANIES), "secretsExposed": False, "valuesReturned": False},
            "storage": {"privateRuntimePath": True, "publicSnapshotsUsed": False},
            "retention": {"policyDays": 90, "automaticDeletionEnabled": False},
            "recovery": {"runbook": "docs/operations/DEPARTMENTAL_DAILY_RUNBOOK.md", "restoreTestRequired": True},
            "roles": DEPARTMENTAL_ROLE_PERMISSIONS,
        }

    def daily_report(self, day: str) -> dict[str, Any]:
        health = self.health(day)
        alerts = self._alerts.list(day)
        return {
            "day": day,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "health": health,
            "alertSummary": {
                "total": len(alerts["alerts"]),
                "critical": sum(item["severity"] == "CRITICAL" for item in alerts["alerts"]),
                "warning": sum(item["severity"] == "WARNING" for item in alerts["alerts"]),
            },
            "alerts": alerts["alerts"],
            "alertEvaluationRequired": alerts.get("evaluationRequired", False),
            "alertsEvaluatedAt": alerts.get("lastEvaluationAt"),
            "reviewRequired": True,
        }

    def weekly_report(self, end_day: str) -> dict[str, Any]:
        end = date.fromisoformat(end_day)
        start = end - timedelta(days=6)
        history = DepartmentalHistoryService(self._facts)
        companies = [
            history.build(company.empresa_codigo, start.isoformat(), end.isoformat())
            for company in LICENSED_COMPANIES
        ]
        return {
            "period": {"start": start.isoformat(), "end": end.isoformat(), "expectedDays": 7},
            "complete": all(not item["missingDays"] for item in companies),
            "companies": companies,
            "comparisonPublished": all(item["comparable"] for item in companies),
            "limitations": [] if all(not item["missingDays"] for item in companies) else ["Semana incompleta; totais parciais visíveis, variações bloqueadas."],
            "reviewRequired": True,
        }
