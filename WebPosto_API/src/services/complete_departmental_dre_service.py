"""DRE departamental completa somente quando todas as fontes estão comprovadas."""

import asyncio
from decimal import Decimal
from typing import Any

from src.core.management_scope import LICENSED_COMPANIES


class CompleteDepartmentalDreService:
    DEPARTMENTS = ("combustiveis", "conveniencia", "lubrificantes")

    def __init__(self, reconciliation: Any, fuel: Any, non_fuel: Any) -> None:
        self._reconciliation = reconciliation
        self._fuel = fuel
        self._non_fuel = non_fuel

    @staticmethod
    def _decimal(value: Any) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value)).quantize(Decimal("0.01"))
        except Exception:
            return None

    @classmethod
    def _walk_department_rows(cls, value: Any) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        if isinstance(value, dict):
            department = value.get("departamento") or value.get("department")
            company = value.get("empresaCodigo") or value.get("companyCode")
            if department in cls.DEPARTMENTS and company is not None:
                found.append(value)
            for child in value.values():
                found.extend(cls._walk_department_rows(child))
        elif isinstance(value, list):
            for child in value:
                found.extend(cls._walk_department_rows(child))
        return found

    async def build(self, start: str, end: str, company_code: int | None = None) -> dict[str, Any]:
        reconciliation, fuel_response, non_fuel_response = await asyncio.gather(
            self._reconciliation.build(start, end, company_code),
            self._fuel.build(start, end, company_code),
            self._non_fuel.build(start, end, company_code),
        )
        selected = [item for item in LICENSED_COMPANIES
                    if company_code is None or item.empresa_codigo == int(company_code)]
        expense_by = {
            (int(row["companyCode"]), row["department"]): self._decimal(row.get("confirmedExpenses"))
            for row in reconciliation.get("departmentalDre") or []
        }
        sales_by: dict[tuple[int, str], dict[str, Any]] = {}

        if getattr(fuel_response, "success", False):
            for company in (fuel_response.data or {}).get("empresas") or []:
                products = company.get("produtos") or []
                revenue = sum((self._decimal(item.get("faturamento")) or Decimal("0") for item in products), Decimal("0"))
                cost = sum((self._decimal(item.get("custoRegistrado")) or Decimal("0") for item in products), Decimal("0"))
                pagination_complete = bool((company.get("pagination") or {}).get("complete"))
                sales_by[(int(company["empresaCodigo"]), "combustiveis")] = {
                    "revenue": revenue,
                    "cost": cost,
                    "complete": pagination_complete,
                    "coveragePct": self._decimal((company.get("cobertura") or {}).get("coberturaPct")),
                    "itemsCollected": int((company.get("cobertura") or {}).get("itensColetados") or 0),
                    "itemsAccepted": int((company.get("cobertura") or {}).get("itensCombustivel") or 0),
                    "itemsQuarantined": int((company.get("cobertura") or {}).get("itensQuarentena") or 0),
                    "pagination": company.get("pagination") or {},
                }

        if getattr(non_fuel_response, "success", False):
            for row in self._walk_department_rows(non_fuel_response.data or {}):
                department = row.get("departamento") or row.get("department")
                if department not in {"conveniencia", "lubrificantes"}:
                    continue
                revenue = self._decimal(row.get("faturamento") or row.get("receita") or row.get("receitaBruta"))
                cost = self._decimal(row.get("custo") or row.get("custoRegistrado") or row.get("custoTotal"))
                complete = bool(row.get("complete", revenue is not None and cost is not None))
                if revenue is not None and cost is not None:
                    sales_by[(int(row.get("empresaCodigo") or row.get("companyCode")), department)] = {
                        "revenue": revenue, "cost": cost, "complete": complete,
                    }

        dre_ready = bool((reconciliation.get("publication") or {}).get("dreTotalsReleased"))
        lines: list[dict[str, Any]] = []
        for company in selected:
            for department in self.DEPARTMENTS:
                sales = sales_by.get((company.empresa_codigo, department))
                expenses = expense_by.get((company.empresa_codigo, department))
                released = bool(dre_ready and sales and sales["complete"] and expenses is not None)
                revenue, cost = (sales["revenue"], sales["cost"]) if sales else (None, None)
                gross_margin = revenue - cost if revenue is not None and cost is not None else None
                result = gross_margin - expenses if gross_margin is not None and expenses is not None else None
                margin_pct = (result / revenue * Decimal("100")) if result is not None and revenue else None
                lines.append({
                    "companyCode": company.empresa_codigo,
                    "companyName": company.nome,
                    "department": department,
                    "revenue": str(revenue) if released else None,
                    "cost": str(cost) if released else None,
                    "grossMargin": str(gross_margin) if released else None,
                    "expenses": str(expenses) if released else None,
                    "operatingResult": str(result) if released else None,
                    "operatingMarginPct": str(margin_pct.quantize(Decimal("0.01"))) if released and margin_pct is not None else None,
                    "status": "LIBERADO" if released else "BLOQUEADO",
                    "operationalEvidence": ({
                        "status": "COMPROVADO" if sales["complete"] else "INCOMPLETO",
                        "revenue": str(revenue),
                        "cost": str(cost),
                        "grossMargin": str(gross_margin),
                        "coveragePct": str(sales.get("coveragePct")) if sales.get("coveragePct") is not None else None,
                        "itemsCollected": sales.get("itemsCollected"),
                        "itemsAccepted": sales.get("itemsAccepted"),
                        "itemsQuarantined": sales.get("itemsQuarantined"),
                        "pagination": sales.get("pagination") or {},
                    } if sales and revenue is not None and cost is not None else None),
                    "missingEvidence": [
                        name for name, missing in (
                            ("CLASSIFICACAO_DESPESAS", not dre_ready or expenses is None),
                            ("FATURAMENTO", revenue is None),
                            ("CUSTO", cost is None),
                            ("COBERTURA_VENDAS", not sales or not sales["complete"]),
                        ) if missing
                    ],
                })
        return {
            "period": {"start": start, "end": end},
            "lines": lines,
            "allReleased": all(row["status"] == "LIBERADO" for row in lines),
            "consolidatedGenericResult": False,
        }
