"""D02 — Motor de pré-conferência automática."""
from __future__ import annotations

from src.domain.reconciliation.models import PreCheckOutcome, PreCheckSummary, ReconciliationItem, ReconciliationStatus
from src.domain.reconciliation.nature_strategies import classify_pre_check, expected_realized
from src.services.cash_operations_service import _round2


class PreReconciliationEngine:
    """Separa AUTO_MATCHED / NEEDS_REVIEW / DIVERGENT sem revisão humana total."""

    def run(self, items: list[ReconciliationItem], persisted: dict[str, dict] | None = None) -> tuple[list[ReconciliationItem], PreCheckSummary]:
        persisted = persisted or {}
        counts = {k: 0 for k in PreCheckOutcome}
        divergent_amount = 0.0

        for item in items:
            state = persisted.get(item.id) or {}
            justifications = item.justifications
            has_just = bool(justifications) or bool(state.get("justifications"))
            stored_status = state.get("status")

            item.valorEsperado = expected_realized(item) or item.valorApurado
            if item.valorRealizado is None:
                item.valorRealizado = item.valorApresentado

            if stored_status == ReconciliationStatus.CONFIRMED.value:
                item.status = ReconciliationStatus.CONFIRMED
                item.preCheckOutcome = PreCheckOutcome.CONFIRMED
            elif stored_status == ReconciliationStatus.JUSTIFIED.value or has_just:
                item.status = ReconciliationStatus.JUSTIFIED
                item.preCheckOutcome = PreCheckOutcome.JUSTIFIED
            else:
                outcome, status = classify_pre_check(item, has_justification=False)
                item.preCheckOutcome = outcome
                item.status = status

            counts[item.preCheckOutcome] += 1
            if item.preCheckOutcome in {PreCheckOutcome.DIVERGENT, PreCheckOutcome.NEEDS_REVIEW}:
                divergent_amount += abs(item.diferenca)

            if state.get("updatedAt"):
                item.updatedAt = state["updatedAt"]
            if state.get("responsibleUser"):
                item.responsibleUser = state["responsibleUser"]

        summary = PreCheckSummary(
            totalAnalyzed=len(items),
            autoMatched=counts[PreCheckOutcome.AUTO_MATCHED],
            needsReview=counts[PreCheckOutcome.NEEDS_REVIEW],
            divergent=counts[PreCheckOutcome.DIVERGENT],
            justified=counts[PreCheckOutcome.JUSTIFIED],
            confirmed=counts[PreCheckOutcome.CONFIRMED],
            divergentAmount=_round2(divergent_amount),
        )
        return items, summary
