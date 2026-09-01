"""Tratativa de despesas pendentes de classificação — Sprint 44."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums.expense_classification import (
    ExpenseClassification,
    ExpenseClassificationDecision,
    ExpenseClassificationStatus,
    PendingExpenseGroup,
)


class ExpensePendingSummary(BaseModel):
    """Resumo de despesas pendentes para o Dashboard."""

    model_config = ConfigDict(frozen=True)

    total_pending_count: int = 0
    total_pending_value: float = 0.0
    groups: list[PendingExpenseGroup] = Field(default_factory=list)
    by_company: dict[int, float] = Field(default_factory=dict)
    alert_level: str = "OK"
    blocks_dre: bool = False
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExpensePendingService:
    """Gerencia despesas não classificadas sem quebrar o pipeline da DRE."""

    PENDING_CENTER = "PENDENTE_CLASSIFICACAO"
    DRE_BLOCK_THRESHOLD = 0.02

    def __init__(self, review_store: Any = None) -> None:
        self._review_store = review_store

    def group_pending_expenses(
        self,
        expenses: list[dict[str, Any]],
        company_revenues: dict[int, float] | None = None,
    ) -> ExpensePendingSummary:
        groups_map: dict[tuple[int, str], dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "total": Decimal("0"), "descricao": None, "empresa_nome": None}
        )

        for expense in expenses:
            classification = self._get_classification(expense)
            if classification not in {ExpenseClassification.PENDENTE, ExpenseClassification.QUARENTENA}:
                continue

            empresa = int(expense.get("empresaCodigo") or 0)
            plano = str(expense.get("planoContasCodigo") or expense.get("planoCodigo") or "SEM_CODIGO")
            valor = Decimal(str(expense.get("valor") or expense.get("amount") or 0))

            key = (empresa, plano)
            groups_map[key]["count"] += 1
            groups_map[key]["total"] += valor
            groups_map[key]["descricao"] = expense.get("planoContasDescricao") or expense.get("descricao")
            groups_map[key]["empresa_nome"] = expense.get("empresaNome")

        groups = [
            PendingExpenseGroup(
                plano_contas_codigo=plano,
                plano_contas_descricao=data["descricao"],
                empresa_codigo=empresa,
                empresa_nome=data["empresa_nome"],
                count=data["count"],
                total_value=float(data["total"]),
                suggested_classification=ExpenseClassification.from_plano_contas(plano),
                status=ExpenseClassificationStatus.PENDING,
            )
            for (empresa, plano), data in groups_map.items()
        ]

        total_count = sum(g.count for g in groups)
        total_value = sum(g.total_value for g in groups)
        by_company = defaultdict(float)
        for g in groups:
            by_company[g.empresa_codigo] += g.total_value

        blocks_dre = False
        if company_revenues:
            for empresa, pending_value in by_company.items():
                revenue = company_revenues.get(empresa, 0)
                if revenue > 0 and pending_value / revenue > self.DRE_BLOCK_THRESHOLD:
                    blocks_dre = True
                    break

        alert_level = "OK"
        if total_value >= 50000:
            alert_level = "CRITICAL"
        elif total_value >= 10000:
            alert_level = "WARNING"
        elif total_count > 0:
            alert_level = "INFO"

        return ExpensePendingSummary(
            total_pending_count=total_count,
            total_pending_value=float(total_value),
            groups=sorted(groups, key=lambda g: -g.total_value),
            by_company=dict(by_company),
            alert_level=alert_level,
            blocks_dre=blocks_dre,
        )

    def _get_classification(self, expense: dict[str, Any]) -> ExpenseClassification:
        raw = expense.get("classificacao") or expense.get("classification")
        if raw:
            try:
                return ExpenseClassification(raw)
            except ValueError:
                pass
        if self._review_store:
            fact_id = expense.get("id") or expense.get("despesaId")
            if fact_id:
                review = self._review_store.get(str(fact_id))
                if review and review.department:
                    dept_map = {
                        "combustiveis": ExpenseClassification.COMBUSTIVEIS,
                        "conveniencia": ExpenseClassification.CONVENIENCIA,
                        "lubrificantes": ExpenseClassification.LUBRIFICANTES,
                    }
                    return dept_map.get(review.department, ExpenseClassification.PENDENTE)
        return ExpenseClassification.PENDENTE

    def apply_classification(
        self,
        expense_id: str,
        plano_contas_codigo: str,
        new_classification: ExpenseClassification,
        reviewer: str,
        rationale: str,
        apply_as_rule: bool = False,
    ) -> ExpenseClassificationDecision:
        decision = ExpenseClassificationDecision(
            expense_id=expense_id,
            plano_contas_codigo=plano_contas_codigo,
            previous_classification=ExpenseClassification.PENDENTE,
            new_classification=new_classification,
            reviewer=reviewer,
            rationale=rationale,
            apply_as_rule=apply_as_rule,
            decided_at=datetime.now(timezone.utc).isoformat(),
        )
        return decision

    def inject_pending_center_in_dre(
        self,
        dre_lines: list[dict[str, Any]],
        pending_summary: ExpensePendingSummary,
    ) -> list[dict[str, Any]]:
        if pending_summary.total_pending_count == 0:
            return dre_lines

        for empresa_codigo, pending_value in pending_summary.by_company.items():
            pending_line = {
                "companyCode": empresa_codigo,
                "department": self.PENDING_CENTER,
                "revenue": None,
                "cost": None,
                "grossMargin": None,
                "expenses": str(pending_value),
                "operatingResult": None,
                "operatingMarginPct": None,
                "status": "PENDENTE_CLASSIFICACAO",
                "isPendingClassification": True,
                "pendingCount": sum(
                    g.count for g in pending_summary.groups if g.empresa_codigo == empresa_codigo
                ),
                "alertLevel": pending_summary.alert_level,
                "missingEvidence": ["CLASSIFICACAO_DESPESAS"],
            }
            dre_lines.append(pending_line)

        return dre_lines
