"""Sprint 3 — KPIs e DRE conservadora por departamento."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from src.core.management_scope import MANAGEMENT_DEPARTMENTS, is_licensed_company
from src.services.departmental_fact_store import DepartmentalFactStore

MONEY_Q = Decimal("0.01")
RATIO_Q = Decimal("0.01")


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_Q, rounding=ROUND_HALF_UP))


def _ratio(numerator: Decimal, denominator: Decimal) -> str | None:
    if denominator == 0:
        return None
    return str(
        ((numerator / denominator) * Decimal("100")).quantize(
            RATIO_Q, rounding=ROUND_HALF_UP
        )
    )


class DepartmentalKpiService:
    def __init__(
        self,
        store: DepartmentalFactStore | None = None,
        *,
        max_quarantine_ratio: Decimal = Decimal("0.02"),
    ) -> None:
        self._store = store or DepartmentalFactStore()
        self._max_quarantine_ratio = max_quarantine_ratio

    @staticmethod
    def _classified(batch: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            fact
            for fact in batch.get("facts") or []
            if fact.get("status") == "CLASSIFIED" and fact.get("departamento")
        ]

    def _batch_complete(self, batch: dict[str, Any]) -> bool:
        facts = batch.get("facts") or []
        quarantine = batch.get("quarantine") or []
        total_count = len(facts) + len(quarantine)
        count_ratio = (
            Decimal(len(quarantine)) / Decimal(total_count)
            if total_count
            else Decimal("0")
        )
        quarantine_value = sum(
            (abs(_decimal(fact.get("valor"))) for fact in quarantine),
            Decimal("0"),
        )
        source_value = abs(_decimal(batch.get("source_total")))
        value_ratio = (
            quarantine_value / source_value
            if source_value
            else (Decimal("1") if quarantine_value else Decimal("0"))
        )
        return (
            count_ratio <= self._max_quarantine_ratio
            and value_ratio <= self._max_quarantine_ratio
            and int(batch.get("identity_conflicts") or 0) == 0
            and _decimal(batch.get("reconciliation_difference")) == 0
        )

    @staticmethod
    def _lineage(facts: list[dict[str, Any]], saved_at: str | None) -> dict[str, Any]:
        endpoints = sorted(
            {
                str((fact.get("lineage") or {}).get("endpoint"))
                for fact in facts
                if (fact.get("lineage") or {}).get("endpoint")
            }
        )
        logical_tokens = sorted(
            {
                str((fact.get("lineage") or {}).get("logical_token"))
                for fact in facts
                if (fact.get("lineage") or {}).get("logical_token")
            }
        )
        return {
            "endpoints": endpoints,
            "logicalTokens": logical_tokens,
            "materializedAt": saved_at,
        }

    def build_dre(self, company_code: int, day: str) -> dict[str, Any] | None:
        if not is_licensed_company(company_code):
            raise ValueError("UNLICENSED_COMPANY")
        stored = self._store.load(company_code, day)
        if not stored:
            return None
        data = stored.get("data") or {}
        batches = data.get("batches") or {}
        sales_batch = batches.get("sales") or {}
        cost_batch = batches.get("costs") or {}
        expense_batch = batches.get("expenses") or {}
        sales = self._classified(sales_batch)
        costs = self._classified(cost_batch)
        expenses = self._classified(expense_batch)

        revenue_by: dict[str, Decimal] = defaultdict(Decimal)
        cost_by: dict[str, Decimal] = defaultdict(Decimal)
        expense_by: dict[str, Decimal] = defaultdict(Decimal)
        quantity_by: dict[str, Decimal] = defaultdict(Decimal)
        transaction_ids_by: dict[str, set[str]] = defaultdict(set)
        transaction_identity_complete: dict[str, bool] = defaultdict(lambda: True)
        for fact in sales:
            department = str(fact["departamento"])
            revenue_by[department] += _decimal(fact.get("valor"))
            quantity_by[department] += _decimal(fact.get("quantidade"))
            source_id = str(fact.get("source_record_id") or "")
            if ":" in source_id:
                transaction_ids_by[department].add(source_id.split(":", 1)[0])
            else:
                transaction_identity_complete[department] = False
        for fact in costs:
            cost_by[str(fact["departamento"])] += _decimal(fact.get("valor"))
        for fact in expenses:
            expense_by[str(fact["departamento"])] += _decimal(fact.get("valor"))

        sales_complete = self._batch_complete(sales_batch)
        costs_complete = self._batch_complete(cost_batch)
        expenses_complete = self._batch_complete(expense_batch)
        all_facts = sales + costs + expenses
        lines: list[dict[str, Any]] = []
        for department in MANAGEMENT_DEPARTMENTS:
            revenue = revenue_by[department]
            cost = cost_by[department]
            gross_margin = revenue - cost
            expense = expense_by[department] if expenses_complete else None
            operating_result = gross_margin - expense if expense is not None else None
            quantity = quantity_by[department]
            transaction_count = len(transaction_ids_by[department])
            if department == "combustiveis":
                specific_metrics = {
                    "liters": str(quantity),
                    "averageSalePricePerLiter": (
                        _money(revenue / quantity) if quantity != 0 else None
                    ),
                    "costPerLiter": _money(cost / quantity) if quantity != 0 else None,
                    "grossMarginPerLiter": (
                        _money(gross_margin / quantity) if quantity != 0 else None
                    ),
                }
            elif department == "conveniencia":
                ticket_available = (
                    transaction_identity_complete[department] and transaction_count > 0
                )
                specific_metrics = {
                    "transactionCount": transaction_count if ticket_available else None,
                    "averageTicket": (
                        _money(revenue / Decimal(transaction_count))
                        if ticket_available
                        else None
                    ),
                    "itemsPerTransaction": (
                        str(
                            (
                                Decimal(
                                    sum(
                                        1
                                        for fact in sales
                                        if fact.get("departamento") == department
                                    )
                                )
                                / Decimal(transaction_count)
                            ).quantize(RATIO_Q, rounding=ROUND_HALF_UP)
                        )
                        if ticket_available
                        else None
                    ),
                }
            else:
                specific_metrics = {
                    "unitsSold": str(quantity),
                    "grossMarginPerUnit": (
                        _money(gross_margin / quantity) if quantity != 0 else None
                    ),
                }
            line = {
                "companyCode": company_code,
                "department": department,
                "period": {"start": day, "end": day},
                "currency": "BRL",
                "revenue": _money(revenue),
                "costOfRevenue": _money(cost),
                "grossMarginValue": _money(gross_margin),
                "grossMarginPercent": _ratio(gross_margin, revenue),
                "operatingExpenses": _money(expense) if expense is not None else None,
                "operatingResult": (
                    _money(operating_result) if operating_result is not None else None
                ),
                "operatingMarginPercent": (
                    _ratio(operating_result, revenue)
                    if operating_result is not None
                    else None
                ),
                "quantity": str(quantity),
                "quantityUnit": "L" if department == "combustiveis" else "UN",
                "marginPerUnit": (
                    _money(gross_margin / quantity)
                    if quantity != 0
                    else None
                ),
                "specificMetrics": specific_metrics,
                "status": (
                    "COMPLETE"
                    if sales_complete and costs_complete and expenses_complete
                    else "PARTIAL_GROSS_MARGIN_ONLY"
                ),
                "limitations": (
                    []
                    if expenses_complete
                    else [
                        "Despesas sem cobertura departamental completa; resultado operacional não publicado."
                    ]
                ),
                "lineage": self._lineage(
                    [
                        fact
                        for fact in all_facts
                        if fact.get("departamento") == department
                    ],
                    stored.get("savedAt"),
                ),
            }
            lines.append(line)

        return {
            "companyCode": company_code,
            "period": {"start": day, "end": day},
            "currency": "BRL",
            "statementType": "DEPARTMENTAL_DRE",
            "reviewRequired": True,
            "publishable": sales_complete and costs_complete and expenses_complete,
            "coverage": {
                "salesComplete": sales_complete,
                "costsComplete": costs_complete,
                "expensesComplete": expenses_complete,
            },
            "lines": lines,
        }
