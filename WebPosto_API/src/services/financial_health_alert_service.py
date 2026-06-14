"""F08.2 — Alertas preventivos de saúde de snapshots financeiros."""
from __future__ import annotations

from typing import Any

from src.services.financial_snapshot_health_service import FinancialSnapshotHealthService


def _alert(
    *,
    code: str,
    severity: str,
    message: str,
    snapshot_type: str | None,
    origin: str | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "snapshotType": snapshot_type,
        "origin": origin or snapshot_type or "financial",
    }


class FinancialHealthAlertService:
    def __init__(self, health: FinancialSnapshotHealthService | None = None) -> None:
        self._health = health or FinancialSnapshotHealthService()

    def generate(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> list[dict[str, Any]]:
        assessment = self._health.assess_key(data_inicial, data_final, empresa_codigo)
        alerts: list[dict[str, Any]] = []
        summary = assessment.get("summary") or {}

        if not summary.get("coverageComplete"):
            gaps = summary.get("coverageGaps") or []
            alerts.append(
                _alert(
                    code="COVERAGE_INCOMPLETE",
                    severity="CRITICAL" if len(gaps) >= 2 else "WARNING",
                    message=f"Cobertura incompleta: {', '.join(gaps) if gaps else 'lacunas detectadas'}",
                    snapshot_type=None,
                    origin="coverage",
                )
            )

        for snap in assessment.get("snapshots") or []:
            label = snap.get("label") or snap.get("snapshotType")
            age = snap.get("snapshotAgeHours")
            confidence = str(snap.get("confidenceLevel") or "").upper()
            origin = snap.get("source") or snap.get("snapshotType")

            if age is not None and age > 72:
                alerts.append(
                    _alert(
                        code="SNAPSHOT_STALE_CRITICAL",
                        severity="CRITICAL",
                        message=f"{label} com idade {age:.1f}h (>72h)",
                        snapshot_type=snap.get("snapshotType"),
                        origin=origin,
                    )
                )
            elif age is not None and age > 24:
                alerts.append(
                    _alert(
                        code="SNAPSHOT_STALE_WARNING",
                        severity="WARNING",
                        message=f"{label} com idade {age:.1f}h (>24h)",
                        snapshot_type=snap.get("snapshotType"),
                        origin=origin,
                    )
                )

            if confidence == "BAIXA":
                alerts.append(
                    _alert(
                        code="CONFIDENCE_LOW",
                        severity="CRITICAL",
                        message=f"{label} com confiança BAIXA",
                        snapshot_type=snap.get("snapshotType"),
                        origin=origin,
                    )
                )

            if snap.get("healthStatus") == "WARNING":
                alerts.append(
                    _alert(
                        code="HEALTH_WARNING",
                        severity="WARNING",
                        message=f"{label} em estado WARNING",
                        snapshot_type=snap.get("snapshotType"),
                        origin=origin,
                    )
                )
            elif snap.get("healthStatus") == "CRITICAL":
                alerts.append(
                    _alert(
                        code="HEALTH_CRITICAL",
                        severity="CRITICAL",
                        message=f"{label} em estado CRITICAL",
                        snapshot_type=snap.get("snapshotType"),
                        origin=origin,
                    )
                )

            if not snap.get("exists"):
                alerts.append(
                    _alert(
                        code="SNAPSHOT_MISSING",
                        severity="CRITICAL",
                        message=f"{label} ausente para o período",
                        snapshot_type=snap.get("snapshotType"),
                        origin=origin,
                    )
                )

        if summary.get("overallStatus") == "HEALTHY" and not alerts:
            alerts.append(
                _alert(
                    code="HEALTH_OK",
                    severity="INFO",
                    message="Snapshots financeiros dentro dos limites de saúde",
                    snapshot_type=None,
                    origin="health_engine",
                )
            )

        severity_rank = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        alerts.sort(key=lambda a: severity_rank.get(str(a.get("severity")), 9))
        if not alerts:
            alerts.append(
                _alert(
                    code="MONITORING_ACTIVE",
                    severity="INFO",
                    message="Motor de alertas operacional",
                    snapshot_type=None,
                    origin="health_engine",
                )
            )
        return alerts

    def active_count(self, alerts: list[dict[str, Any]]) -> dict[str, int]:
        counts = {"INFO": 0, "WARNING": 0, "CRITICAL": 0}
        for alert in alerts:
            sev = str(alert.get("severity") or "INFO").upper()
            if sev in counts:
                counts[sev] += 1
        return counts


_alert_service: FinancialHealthAlertService | None = None


def get_alert_service() -> FinancialHealthAlertService:
    global _alert_service
    if _alert_service is None:
        _alert_service = FinancialHealthAlertService()
    return _alert_service
