"""Sprints 5 e 6 — leituras da Presidência e da Diretoria sobre a mesma base."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.core.management_scope import LICENSED_COMPANIES, MANAGEMENT_DEPARTMENTS
from src.services.departmental_comparison_service import DepartmentalComparisonService
from src.services.departmental_history_service import DepartmentalHistoryService
from src.services.departmental_kpi_service import DepartmentalKpiService


def _number(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


class DepartmentalExecutiveService:
    def __init__(
        self,
        kpis: DepartmentalKpiService | None = None,
        comparisons: DepartmentalComparisonService | None = None,
        history: DepartmentalHistoryService | None = None,
    ) -> None:
        self._kpis = kpis or DepartmentalKpiService()
        self._comparisons = comparisons or DepartmentalComparisonService(self._kpis)
        self._history = history or DepartmentalHistoryService(kpis=self._kpis)

    def cockpit(self, day: str) -> dict[str, Any]:
        comparison = self._comparisons.build(day)
        blocks = []
        decisions = []
        for item in comparison["departments"]:
            ranking = item["ranking"]
            best, worst = (ranking[0], ranking[-1]) if ranking else (None, None)
            risk = None
            if item["excludedCompanies"]:
                risk = "Cobertura não equivalente; comparação executiva bloqueada."
            elif worst and _number(worst["grossMarginValue"]) <= 0:
                risk = "Empresa com margem bruta não positiva."
            blocks.append({
                "department": item["department"],
                "metric": "grossMarginValue",
                "bestCompany": best,
                "worstCompany": worst,
                "trend": None,
                "operatingProfit": None,
                "risk": risk or "Sem risco material reproduzível com apenas um dia.",
                "evidence": {"period": item["period"], "ranking": ranking},
            })
            if risk:
                decisions.append({
                    "priority": len(decisions) + 1,
                    "department": item["department"],
                    "decision": "Completar e reconciliar a cobertura antes de decidir.",
                    "estimatedImpactBRL": None,
                    "suggestedOwner": "Diretoria Financeira",
                    "dueInDays": 1,
                    "evidence": item["excludedCompanies"],
                })
        return {
            "audience": "PRESIDENCIA",
            "period": comparison["period"],
            "dataCoverage": {"complete": not comparison["missingCompanies"], "missingCompanies": comparison["missingCompanies"]},
            "blocks": blocks,
            "priorityDecisions": decisions[:5],
            "limitations": [
                "Lucro operacional indisponível enquanto despesas não tiverem classificação departamental completa.",
                "Tendência indisponível até haver períodos históricos equivalentes completos.",
            ],
            "reviewRequired": True,
        }

    def director_panels(self, company_code: int, start_day: str, end_day: str) -> dict[str, Any]:
        trend = self._history.build(company_code, start_day, end_day)
        statement = self._kpis.build_dre(company_code, end_day)
        if statement is None:
            return {"companyCode": company_code, "period": trend["period"], "available": False, "panels": {}}
        lines = {line["department"]: line for line in statement["lines"]}
        panels = {
            "financial": {
                "owner": "Diretoria Financeira",
                "action": "Classificar despesas pendentes e reconciliar a DRE.",
                "departments": [lines[department] for department in MANAGEMENT_DEPARTMENTS],
                "coverage": statement["coverage"],
            },
            "commercial": {
                "owner": "Diretoria Comercial",
                "action": "Atuar sobre margem, ticket e mix dentro de cada departamento.",
                "departments": [
                    {"department": department, "revenue": lines[department]["revenue"], "grossMarginValue": lines[department]["grossMarginValue"], "grossMarginPercent": lines[department]["grossMarginPercent"], "specificMetrics": lines[department]["specificMetrics"]}
                    for department in MANAGEMENT_DEPARTMENTS
                ],
                "temporalComparison": trend["departments"],
            },
            "operational": {
                "owner": "Diretoria Operacional",
                "action": "Investigar estoque e dados em quarentena; perdas e LMC ainda não integrados.",
                "availableMetrics": [],
                "limitations": ["Perdas, rupturas, LMC e produtividade ainda não possuem fatos departamentais equivalentes."],
            },
        }
        return {
            "companyCode": company_code,
            "period": trend["period"],
            "available": True,
            "filters": {"companyCode": company_code, "start": start_day, "end": end_day},
            "panels": panels,
            "lineageVisible": True,
            "exportRows": [
                {"companyCode": company_code, "department": line["department"], "periodStart": start_day, "periodEnd": end_day, "revenue": line["revenue"], "grossMarginValue": line["grossMarginValue"], "status": line["status"], "lineage": line["lineage"]}
                for line in statement["lines"]
            ],
        }
