"""Validação de integridade de paginação — Sprint 44."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PaginationIntegrityResult(BaseModel):
    """Resultado da validação de integridade de paginação."""

    model_config = ConfigDict(frozen=True)

    endpoint: str
    empresa_codigo: int
    period_start: str
    period_end: str
    expected_total: int | None = None
    collected_total: int
    duplicates_removed: int = 0
    pages_fetched: int
    termination_reason: str
    is_complete: bool
    integrity_status: str
    variance_pct: float | None = None
    alert_level: str = "OK"
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def has_data_loss_risk(self) -> bool:
        if self.expected_total is None:
            return not self.is_complete
        return self.collected_total < self.expected_total


class PaginationIntegrityService:
    """Valida completude da ingestão de dados paginados."""

    VARIANCE_THRESHOLD_PCT = 0.5

    def validate(
        self,
        endpoint: str,
        empresa_codigo: int,
        period_start: str,
        period_end: str,
        pagination_metadata: dict[str, Any],
        expected_total: int | None = None,
    ) -> PaginationIntegrityResult:
        collected = len(pagination_metadata.get("resultados", []))
        pages = pagination_metadata.get("pagination", {}).get("pages", 0)
        duplicates = pagination_metadata.get("pagination", {}).get("duplicatesRemoved", 0)
        termination = pagination_metadata.get("pagination", {}).get("termination", "UNKNOWN")
        complete = pagination_metadata.get("pagination", {}).get("complete", False)

        variance_pct = None
        if expected_total is not None and expected_total > 0:
            variance_pct = round(abs(collected - expected_total) / expected_total * 100, 2)

        if not complete:
            integrity_status = "INCOMPLETE"
            alert_level = "CRITICAL"
        elif expected_total is not None and variance_pct is not None:
            if variance_pct > self.VARIANCE_THRESHOLD_PCT:
                integrity_status = "VARIANCE_DETECTED"
                alert_level = "WARNING"
            else:
                integrity_status = "VERIFIED"
                alert_level = "OK"
        else:
            integrity_status = "COMPLETE_UNVERIFIED"
            alert_level = "INFO"

        return PaginationIntegrityResult(
            endpoint=endpoint,
            empresa_codigo=empresa_codigo,
            period_start=period_start,
            period_end=period_end,
            expected_total=expected_total,
            collected_total=collected,
            duplicates_removed=duplicates,
            pages_fetched=pages,
            termination_reason=termination,
            is_complete=complete,
            integrity_status=integrity_status,
            variance_pct=variance_pct,
            alert_level=alert_level,
        )

    def validate_batch(
        self,
        results: list[tuple[str, int, str, str, dict[str, Any], int | None]],
    ) -> list[PaginationIntegrityResult]:
        return [
            self.validate(endpoint, empresa, start, end, metadata, expected)
            for endpoint, empresa, start, end, metadata, expected in results
        ]

    def summarize(self, results: list[PaginationIntegrityResult]) -> dict[str, Any]:
        total = len(results)
        complete = sum(1 for r in results if r.is_complete)
        with_variance = sum(1 for r in results if r.integrity_status == "VARIANCE_DETECTED")
        incomplete = sum(1 for r in results if not r.is_complete)
        critical = [r for r in results if r.alert_level == "CRITICAL"]

        return {
            "total_validations": total,
            "complete": complete,
            "with_variance": with_variance,
            "incomplete": incomplete,
            "overall_status": "CRITICAL" if critical else ("WARNING" if with_variance else "OK"),
            "critical_endpoints": [
                {
                    "endpoint": r.endpoint,
                    "empresa_codigo": r.empresa_codigo,
                    "collected": r.collected_total,
                    "expected": r.expected_total,
                    "reason": r.termination_reason,
                }
                for r in critical
            ],
            "data_loss_risk": any(r.has_data_loss_risk for r in results),
        }
