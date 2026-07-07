"""DIR-01D — seleção de evidence_items pendentes de identificação nominal."""

from __future__ import annotations

from src.services.decision_evidence.models import DecisionEvidenceItem

PENDING_MATCH_STATUSES = frozenset({"NO_MATCH", "AMBIGUOUS"})


def item_needs_nominal_review(item: DecisionEvidenceItem) -> bool:
    """Itens sem beneficiário identificado que entram na solicitação de conferência."""
    if item.person_name:
        return False
    status = (item.match_status or "NO_MATCH").upper()
    return status in PENDING_MATCH_STATUSES


def partition_evidence_items(
    items: list[DecisionEvidenceItem],
) -> tuple[list[DecisionEvidenceItem], list[DecisionEvidenceItem]]:
    """Retorna (identificados, pendentes de conferência)."""
    identified: list[DecisionEvidenceItem] = []
    pending: list[DecisionEvidenceItem] = []
    for item in items:
        if item_needs_nominal_review(item):
            pending.append(item)
        elif item.person_name:
            identified.append(item)
    return identified, pending


def summarize_pending(items: list[DecisionEvidenceItem]) -> dict[str, float | int]:
    pending = [i for i in items if item_needs_nominal_review(i)]
    identified = [i for i in items if i.person_name and not item_needs_nominal_review(i)]
    return {
        "pending_count": len(pending),
        "pending_amount": round(sum(i.amount for i in pending), 2),
        "identified_count": len(identified),
        "identified_amount": round(sum(i.amount for i in identified), 2),
        "pending_item_ids": [i.id for i in pending],
    }
