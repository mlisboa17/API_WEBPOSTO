"""D02 — Audit Signal Engine determinístico."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from src.domain.reconciliation.models import (
    AuditSeverity,
    AuditSignal,
    AuditSignalType,
    JustificationCategory,
    ReconciliationItem,
    ReconciliationStatus,
)
from src.services.cash_operations_service import _round2

DEFAULT_THRESHOLD = 100.0
RECURRING_MIN = 2
OTHER_EXCESSIVE_RATIO = 0.35


class AuditSignalEngine:
    """Sinais determinísticos — sem acusação de fraude."""

    def __init__(self, threshold: float = DEFAULT_THRESHOLD) -> None:
        self._threshold = threshold

    def evaluate(
        self,
        items: list[ReconciliationItem],
        history_items: list[ReconciliationItem] | None = None,
    ) -> list[AuditSignal]:
        signals: list[AuditSignal] = []
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        history = history_items or []

        for item in items:
            if item.status in {ReconciliationStatus.DIVERGENT, ReconciliationStatus.NEEDS_REVIEW} and not item.justifications:
                signals.append(
                    AuditSignal(
                        signalType=AuditSignalType.UNJUSTIFIED_DIVERGENCE,
                        severity=AuditSeverity.MEDIUM if abs(item.diferenca) < self._threshold else AuditSeverity.HIGH,
                        entityType="RECONCILIATION_ITEM",
                        entityId=item.id,
                        amount=_round2(abs(item.diferenca)),
                        occurrenceCount=1,
                        firstOccurrence=item.periodoInicio,
                        lastOccurrence=item.periodoFim,
                        explanation="DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada",
                    )
                )
            if abs(item.diferenca) >= self._threshold and item.status not in {
                ReconciliationStatus.CONFIRMED,
                ReconciliationStatus.JUSTIFIED,
                ReconciliationStatus.AUTO_MATCHED,
            }:
                signals.append(
                    AuditSignal(
                        signalType=AuditSignalType.THRESHOLD_EXCEEDED,
                        severity=AuditSeverity.HIGH,
                        entityType="RECONCILIATION_ITEM",
                        entityId=item.id,
                        amount=_round2(abs(item.diferenca)),
                        occurrenceCount=1,
                        firstOccurrence=item.periodoInicio,
                        lastOccurrence=item.periodoFim,
                        explanation=f"DIVERGÊNCIA acima do limite configurável (R$ {self._threshold:.2f})",
                    )
                )
            for just in item.justifications:
                if just.reasonCategory == JustificationCategory.OTHER:
                    signals.append(
                        AuditSignal(
                            signalType=AuditSignalType.EXCESSIVE_OTHER,
                            severity=AuditSeverity.LOW,
                            entityType="JUSTIFICATION",
                            entityId=just.id,
                            amount=_round2(abs(item.diferenca)),
                            occurrenceCount=1,
                            firstOccurrence=just.createdAt,
                            lastOccurrence=just.createdAt,
                            explanation="Justificativa OTHER — revisão recomendada",
                        )
                    )
                if just.expectedResolutionDate and just.expectedResolutionDate < now[:10] and item.status not in {
                    ReconciliationStatus.CONFIRMED,
                    ReconciliationStatus.AUTO_MATCHED,
                }:
                    signals.append(
                        AuditSignal(
                            signalType=AuditSignalType.OVERDUE_OPEN,
                            severity=AuditSeverity.MEDIUM,
                            entityType="RECONCILIATION_ITEM",
                            entityId=item.id,
                            amount=_round2(abs(item.diferenca)),
                            occurrenceCount=1,
                            firstOccurrence=just.expectedResolutionDate,
                            lastOccurrence=now[:10],
                            explanation="Divergência vencida permanece aberta — EVIDÊNCIA AUSENTE ou resolução pendente",
                        )
                    )

        nature_counter: Counter[str] = Counter()
        caixa_counter: Counter[str] = Counter()
        for hist in history + items:
            if abs(hist.diferenca) > 0.01:
                nature_counter[hist.paymentNature.value] += 1
                if hist.caixaCodigo is not None:
                    caixa_counter[str(hist.caixaCodigo)] += 1

        for nature, count in nature_counter.items():
            if count >= RECURRING_MIN:
                signals.append(
                    AuditSignal(
                        signalType=AuditSignalType.RECURRING_NATURE,
                        severity=AuditSeverity.MEDIUM,
                        entityType="PAYMENT_NATURE",
                        entityId=nature,
                        amount=0.0,
                        occurrenceCount=count,
                        firstOccurrence=items[0].periodoInicio if items else now[:10],
                        lastOccurrence=items[0].periodoFim if items else now[:10],
                        explanation=f"PADRÃO RECORRENTE — natureza {nature} diverge repetidamente",
                    )
                )
        for caixa, count in caixa_counter.items():
            if count >= RECURRING_MIN:
                signals.append(
                    AuditSignal(
                        signalType=AuditSignalType.RECURRING_CAIXA,
                        severity=AuditSeverity.MEDIUM,
                        entityType="CAIXA",
                        entityId=caixa,
                        amount=0.0,
                        occurrenceCount=count,
                        firstOccurrence=items[0].periodoInicio if items else now[:10],
                        lastOccurrence=items[0].periodoFim if items else now[:10],
                        explanation=f"PADRÃO RECORRENTE — caixa {caixa} com divergências recorrentes",
                    )
                )

        other_count = sum(1 for i in items for j in i.justifications if j.reasonCategory == JustificationCategory.OTHER)
        total_just = sum(len(i.justifications) for i in items)
        if total_just and other_count / total_just >= OTHER_EXCESSIVE_RATIO:
            signals.append(
                AuditSignal(
                    signalType=AuditSignalType.EXCESSIVE_OTHER,
                    severity=AuditSeverity.MEDIUM,
                    entityType="PERIOD",
                    entityId=f"{items[0].periodoInicio}_{items[0].periodoFim}" if items else "unknown",
                    amount=0.0,
                    occurrenceCount=other_count,
                    firstOccurrence=items[0].periodoInicio if items else now[:10],
                    lastOccurrence=items[0].periodoFim if items else now[:10],
                    explanation="Uso excessivo de justificativa OTHER no período — revisão recomendada",
                )
            )

        return signals
