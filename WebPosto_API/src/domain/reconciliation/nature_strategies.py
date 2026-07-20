"""D02 — Estratégias de validação por natureza financeira."""
from __future__ import annotations

from src.domain.reconciliation.models import (
    PaymentNatureCode,
    PreCheckOutcome,
    ReconciliationItem,
    ReconciliationStatus,
)

TOLERANCE = 0.01
DIVERGENT_THRESHOLD = 10.0


def classify_pre_check(item: ReconciliationItem, has_justification: bool = False) -> tuple[PreCheckOutcome, ReconciliationStatus]:
    diff = abs(item.diferenca)
    if has_justification:
        return PreCheckOutcome.JUSTIFIED, ReconciliationStatus.JUSTIFIED
    if diff <= TOLERANCE:
        return PreCheckOutcome.AUTO_MATCHED, ReconciliationStatus.AUTO_MATCHED
    if item.paymentNature == PaymentNatureCode.CARTAO and not item.cardBreakdown:
        return PreCheckOutcome.NEEDS_REVIEW, ReconciliationStatus.NEEDS_REVIEW
    if item.paymentNature == PaymentNatureCode.DINHEIRO and item.sangria and abs(item.valorApresentado - item.sangria) > TOLERANCE:
        return PreCheckOutcome.NEEDS_REVIEW, ReconciliationStatus.NEEDS_REVIEW
    if diff >= DIVERGENT_THRESHOLD:
        return PreCheckOutcome.DIVERGENT, ReconciliationStatus.DIVERGENT
    return PreCheckOutcome.NEEDS_REVIEW, ReconciliationStatus.NEEDS_REVIEW


def expected_realized(item: ReconciliationItem) -> float | None:
    """Calcula valor esperado/realizado conforme estratégia da natureza."""
    nature = item.paymentNature
    if nature == PaymentNatureCode.DINHEIRO:
        sangria = item.sangria or 0.0
        return round(item.valorApurado - sangria, 2)
    if nature == PaymentNatureCode.CARTAO and item.cardBreakdown:
        nets = [c.expectedNet for c in item.cardBreakdown if c.expectedNet is not None]
        if nets:
            return round(sum(nets), 2)
    if nature in {
        PaymentNatureCode.TRANSFERENCIA_CREDITO,
        PaymentNatureCode.TRANSFERENCIA_DEBITO,
        PaymentNatureCode.CHEQUE_VISTA,
        PaymentNatureCode.CHEQUE_PRE,
    }:
        return item.valorApurado
    return item.valorApurado
