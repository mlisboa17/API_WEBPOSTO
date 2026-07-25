"""Sprint 4 — histórico e variações entre períodos equivalentes."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from src.core.management_scope import MANAGEMENT_DEPARTMENTS, is_licensed_company
from src.services.departmental_fact_store import DepartmentalFactStore
from src.services.departmental_kpi_service import DepartmentalKpiService


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _percent(delta: Decimal, base: Decimal) -> str | None:
    if base == 0:
        return None
    return str(((delta / abs(base)) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


class DepartmentalHistoryService:
    def __init__(
        self,
        store: DepartmentalFactStore | None = None,
        kpis: DepartmentalKpiService | None = None,
    ) -> None:
        self._store = store or DepartmentalFactStore()
        self._kpis = kpis or DepartmentalKpiService(self._store)

    @staticmethod
    def _dates(start: date, end: date) -> list[str]:
        return [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]

    def build(self, company_code: int, start_day: str, end_day: str) -> dict[str, Any]:
        if not is_licensed_company(company_code):
            raise ValueError("UNLICENSED_COMPANY")
        start, end = date.fromisoformat(start_day), date.fromisoformat(end_day)
        if end < start:
            raise ValueError("INVALID_PERIOD")
        if (end - start).days > 365:
            raise ValueError("PERIOD_TOO_LARGE")
        expected = self._dates(start, end)
        available = set(self._store.list_days(company_code))
        missing = [day for day in expected if day not in available]
        daily = [
            statement
            for day in expected
            if day in available and (statement := self._kpis.build_dre(company_code, day))
        ]
        prior_end = start - timedelta(days=1)
        prior_start = prior_end - timedelta(days=len(expected) - 1)
        prior_expected = self._dates(prior_start, prior_end)
        prior_missing = [day for day in prior_expected if day not in available]
        prior_daily = [
            statement
            for day in prior_expected
            if day in available and (statement := self._kpis.build_dre(company_code, day))
        ]
        non_equivalent = [
            statement["period"]["start"]
            for statement in daily
            if not (
                (statement.get("coverage") or {}).get("salesComplete") is True
                and (statement.get("coverage") or {}).get("costsComplete") is True
            )
        ]
        prior_non_equivalent = [
            statement["period"]["start"]
            for statement in prior_daily
            if not (
                (statement.get("coverage") or {}).get("salesComplete") is True
                and (statement.get("coverage") or {}).get("costsComplete") is True
            )
        ]
        comparable = (
            not missing
            and not prior_missing
            and not non_equivalent
            and not prior_non_equivalent
            and bool(daily)
            and bool(prior_daily)
        )

        def aggregate(statements: list[dict[str, Any]], department: str) -> dict[str, Decimal]:
            values = {"revenue": Decimal("0"), "costOfRevenue": Decimal("0"), "grossMarginValue": Decimal("0")}
            for statement in statements:
                line = next(item for item in statement["lines"] if item["department"] == department)
                for field in values:
                    values[field] += _decimal(line.get(field))
            return values

        departments = []
        for department in MANAGEMENT_DEPARTMENTS:
            current = aggregate(daily, department)
            prior = aggregate(prior_daily, department)
            variances = {}
            for field in current:
                delta = current[field] - prior[field]
                variances[field] = {
                    "current": _money(current[field]),
                    "prior": _money(prior[field]) if prior_daily else None,
                    "absolute": _money(delta) if comparable else None,
                    "percent": _percent(delta, prior[field]) if comparable else None,
                }
            departments.append({"department": department, "comparable": comparable, "variances": variances})

        return {
            "companyCode": company_code,
            "period": {"start": start.isoformat(), "end": end.isoformat(), "expectedDays": len(expected)},
            "priorPeriod": {"start": prior_start.isoformat(), "end": prior_end.isoformat(), "expectedDays": len(prior_expected)},
            "comparisonRule": "SAME_COMPANY_SAME_DEPARTMENT_EQUIVALENT_COMPLETE_PERIODS",
            "comparable": comparable,
            "missingDays": missing,
            "priorMissingDays": prior_missing,
            "nonEquivalentDays": non_equivalent,
            "priorNonEquivalentDays": prior_non_equivalent,
            "dailyStatements": daily,
            "departments": departments,
            "reviewRequired": True,
        }
