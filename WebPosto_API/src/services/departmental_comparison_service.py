"""Sprint 4 — comparações equivalentes entre empresas do mesmo departamento."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.core.management_scope import LICENSED_COMPANIES, MANAGEMENT_DEPARTMENTS
from src.services.departmental_kpi_service import DepartmentalKpiService


class DepartmentalComparisonService:
    def __init__(self, kpis: DepartmentalKpiService | None = None) -> None:
        self._kpis = kpis or DepartmentalKpiService()

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except Exception:
            return Decimal("0")

    def build(self, day: str) -> dict[str, Any]:
        statements: dict[int, dict[str, Any]] = {}
        missing: list[int] = []
        for company in LICENSED_COMPANIES:
            statement = self._kpis.build_dre(company.empresa_codigo, day)
            if statement is None:
                missing.append(company.empresa_codigo)
                continue
            statements[company.empresa_codigo] = statement

        comparisons: list[dict[str, Any]] = []
        for department in MANAGEMENT_DEPARTMENTS:
            candidates: list[dict[str, Any]] = []
            excluded: list[dict[str, Any]] = []
            for company in LICENSED_COMPANIES:
                statement = statements.get(company.empresa_codigo)
                if not statement:
                    excluded.append(
                        {
                            "companyCode": company.empresa_codigo,
                            "reason": "BATCH_NOT_MATERIALIZED",
                        }
                    )
                    continue
                coverage = statement.get("coverage") or {}
                line = next(
                    (
                        item
                        for item in statement.get("lines") or []
                        if item.get("department") == department
                    ),
                    None,
                )
                if (
                    line is None
                    or coverage.get("salesComplete") is not True
                    or coverage.get("costsComplete") is not True
                ):
                    excluded.append(
                        {
                            "companyCode": company.empresa_codigo,
                            "reason": "NON_EQUIVALENT_COVERAGE",
                        }
                    )
                    continue
                candidates.append(
                    {
                        "companyCode": company.empresa_codigo,
                        "companyName": company.nome,
                        "revenue": line["revenue"],
                        "grossMarginValue": line["grossMarginValue"],
                        "grossMarginPercent": line["grossMarginPercent"],
                        "lineage": line.get("lineage") or {},
                    }
                )

            ranked = sorted(
                candidates,
                key=lambda item: self._decimal(item["grossMarginValue"]),
                reverse=True,
            )
            best_value = (
                self._decimal(ranked[0]["grossMarginValue"]) if ranked else Decimal("0")
            )
            ranking: list[dict[str, Any]] = []
            for position, item in enumerate(ranked, start=1):
                value = self._decimal(item["grossMarginValue"])
                ranking.append(
                    {
                        **item,
                        "position": position,
                        "gapToBestGrossMargin": str((best_value - value).quantize(Decimal("0.01"))),
                    }
                )
            comparisons.append(
                {
                    "department": department,
                    "period": {"start": day, "end": day},
                    "currency": "BRL",
                    "basesEquivalent": len(ranking) >= 2 and not excluded,
                    "rankingMetric": "grossMarginValue",
                    "ranking": ranking,
                    "excludedCompanies": excluded,
                    "bestCompanyCode": ranking[0]["companyCode"] if ranking else None,
                    "worstCompanyCode": ranking[-1]["companyCode"] if ranking else None,
                }
            )

        return {
            "period": {"start": day, "end": day},
            "currency": "BRL",
            "comparisonRule": "SAME_DEPARTMENT_SAME_PERIOD_ONLY",
            "missingCompanies": missing,
            "departments": comparisons,
        }

