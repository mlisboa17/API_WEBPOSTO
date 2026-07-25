"""Serviço de rateio de custos compartilhados — Sprint 45."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AllocationMethod(str):
    PERCENTAGE = "PERCENTAGE"
    FIXED_VALUE = "FIXED_VALUE"
    REVENUE_PROPORTIONAL = "REVENUE_PROPORTIONAL"


class AllocationRule(BaseModel):
    """Regra de rateio de custo compartilhado."""

    model_config = ConfigDict(frozen=True)

    rule_id: str
    management_account_code: str
    description: str | None = None
    method: str = AllocationMethod.PERCENTAGE
    allocations: dict[str, float] = Field(default_factory=dict)
    reviewer: str = Field(min_length=2)
    rationale: str = Field(min_length=3)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    active: bool = True

    @field_validator("allocations")
    @classmethod
    def validate_allocations(cls, value: dict[str, float]) -> dict[str, float]:
        allowed = {"combustiveis", "conveniencia", "lubrificantes"}
        for dept in value:
            if dept not in allowed:
                raise ValueError(f"Departamento inválido: {dept}")
        return value

    def validate_percentage_sum(self) -> bool:
        if self.method != AllocationMethod.PERCENTAGE:
            return True
        total = sum(self.allocations.values())
        return abs(total - 100.0) < 0.01


class AllocationResult(BaseModel):
    """Resultado do rateio de um custo."""

    model_config = ConfigDict(frozen=True)

    source_expense_id: str
    management_account_code: str
    original_value: float
    method: str
    allocations: list[dict[str, Any]]
    allocated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CostAllocationService:
    """Executa rateio de custos compartilhados entre departamentos."""

    DEPARTMENTS = ("combustiveis", "conveniencia", "lubrificantes")

    def __init__(self, rules_store: Any = None) -> None:
        self._rules_store = rules_store
        self._rules_cache: dict[str, AllocationRule] = {}

    def register_rule(self, rule: AllocationRule) -> AllocationRule:
        if rule.method == AllocationMethod.PERCENTAGE and not rule.validate_percentage_sum():
            raise ValueError("Percentuais de rateio devem somar 100%")
        self._rules_cache[rule.management_account_code] = rule
        if self._rules_store:
            self._rules_store.save_allocation_rule(rule)
        return rule

    def get_rule(self, management_account_code: str) -> AllocationRule | None:
        if management_account_code in self._rules_cache:
            return self._rules_cache[management_account_code]
        if self._rules_store:
            rule = self._rules_store.get_allocation_rule(management_account_code)
            if rule:
                self._rules_cache[management_account_code] = rule
            return rule
        return None

    def allocate(
        self,
        expense_id: str,
        management_account_code: str,
        value: float,
        company_revenues: dict[str, float] | None = None,
    ) -> AllocationResult:
        rule = self.get_rule(management_account_code)
        if not rule or not rule.active:
            return self._allocate_equal(expense_id, management_account_code, value)

        if rule.method == AllocationMethod.PERCENTAGE:
            return self._allocate_percentage(expense_id, management_account_code, value, rule)
        elif rule.method == AllocationMethod.REVENUE_PROPORTIONAL:
            return self._allocate_by_revenue(
                expense_id, management_account_code, value, company_revenues or {}
            )
        elif rule.method == AllocationMethod.FIXED_VALUE:
            return self._allocate_fixed(expense_id, management_account_code, value, rule)
        else:
            return self._allocate_equal(expense_id, management_account_code, value)

    def _allocate_percentage(
        self,
        expense_id: str,
        code: str,
        value: float,
        rule: AllocationRule,
    ) -> AllocationResult:
        original = Decimal(str(value))
        allocations = []
        allocated_total = Decimal("0")

        sorted_depts = sorted(rule.allocations.items(), key=lambda x: -x[1])
        for i, (dept, pct) in enumerate(sorted_depts):
            if i == len(sorted_depts) - 1:
                allocated = original - allocated_total
            else:
                allocated = (original * Decimal(str(pct)) / Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            allocated_total += allocated
            allocations.append({
                "department": dept,
                "percentage": pct,
                "allocated_value": float(allocated),
            })

        return AllocationResult(
            source_expense_id=expense_id,
            management_account_code=code,
            original_value=value,
            method=AllocationMethod.PERCENTAGE,
            allocations=allocations,
        )

    def _allocate_by_revenue(
        self,
        expense_id: str,
        code: str,
        value: float,
        revenues: dict[str, float],
    ) -> AllocationResult:
        total_revenue = sum(revenues.get(d, 0) for d in self.DEPARTMENTS)
        if total_revenue <= 0:
            return self._allocate_equal(expense_id, code, value)

        original = Decimal(str(value))
        allocations = []
        allocated_total = Decimal("0")

        dept_list = list(self.DEPARTMENTS)
        for i, dept in enumerate(dept_list):
            dept_revenue = Decimal(str(revenues.get(dept, 0)))
            pct = float(dept_revenue / Decimal(str(total_revenue)) * 100)

            if i == len(dept_list) - 1:
                allocated = original - allocated_total
            else:
                allocated = (original * dept_revenue / Decimal(str(total_revenue))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            allocated_total += allocated
            allocations.append({
                "department": dept,
                "percentage": round(pct, 2),
                "allocated_value": float(allocated),
                "revenue_base": float(dept_revenue),
            })

        return AllocationResult(
            source_expense_id=expense_id,
            management_account_code=code,
            original_value=value,
            method=AllocationMethod.REVENUE_PROPORTIONAL,
            allocations=allocations,
        )

    def _allocate_fixed(
        self,
        expense_id: str,
        code: str,
        value: float,
        rule: AllocationRule,
    ) -> AllocationResult:
        allocations = [
            {"department": dept, "fixed_value": fixed, "allocated_value": fixed}
            for dept, fixed in rule.allocations.items()
        ]
        allocated_sum = sum(a["allocated_value"] for a in allocations)
        remainder = value - allocated_sum
        if remainder != 0 and allocations:
            allocations[0]["allocated_value"] += remainder
            allocations[0]["remainder_adjustment"] = remainder

        return AllocationResult(
            source_expense_id=expense_id,
            management_account_code=code,
            original_value=value,
            method=AllocationMethod.FIXED_VALUE,
            allocations=allocations,
        )

    def _allocate_equal(
        self,
        expense_id: str,
        code: str,
        value: float,
    ) -> AllocationResult:
        original = Decimal(str(value))
        per_dept = (original / Decimal("3")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        remainder = original - (per_dept * 3)

        allocations = []
        for i, dept in enumerate(self.DEPARTMENTS):
            allocated = per_dept + (remainder if i == 0 else Decimal("0"))
            allocations.append({
                "department": dept,
                "percentage": 33.33,
                "allocated_value": float(allocated),
            })

        return AllocationResult(
            source_expense_id=expense_id,
            management_account_code=code,
            original_value=value,
            method="EQUAL_DISTRIBUTION",
            allocations=allocations,
        )

    def apply_allocations_to_dre(
        self,
        dre_lines: list[dict[str, Any]],
        allocations: list[AllocationResult],
    ) -> list[dict[str, Any]]:
        dept_adjustments: dict[tuple[int, str], Decimal] = {}

        for alloc in allocations:
            for item in alloc.allocations:
                dept = item["department"]
                value = Decimal(str(item["allocated_value"]))
                for line in dre_lines:
                    if line.get("department") == dept:
                        key = (line["companyCode"], dept)
                        dept_adjustments[key] = dept_adjustments.get(key, Decimal("0")) + value

        for line in dre_lines:
            key = (line["companyCode"], line.get("department"))
            if key in dept_adjustments:
                current = Decimal(str(line.get("expenses") or 0))
                line["expenses"] = str(current + dept_adjustments[key])
                line["hasAllocatedCosts"] = True
                line["allocatedCostsValue"] = float(dept_adjustments[key])

        return dre_lines
