"""
Execution Feedback Service — EXEC-03 (Integração com Owner Intelligence Engine)

Closes the loop: results confirmed by the owner (SIM/PARCIAL/NÃO) feed back
into the priority scoring of future daily decisions.

If the owner has repeatedly rejected decisions from a given category with
reasons like "not_priority" or "already_resolved", that category's future
score is dampened so it stops crowding out more relevant decisions.

This is a soft, reversible signal (a score multiplier), never a hard filter —
the LOGOS never hides a category, it only lowers its relative priority.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Optional

from .models import DecisionStatus, RejectionReason

logger = logging.getLogger(__name__)

# Keywords used to bridge decision_category (detector class names, e.g.
# "CardReceivableDetector") with the owner_intelligence finding types
# (e.g. risk_type="card_reconciliation"). Order matters: first match wins.
_CATEGORY_KEYWORDS = [
    "card",
    "expense",
    "revenue",
    "margin",
    "supplier",
    "fuel",
    "voucher",
    "receivable",
    "cash",
]

# Rejection reasons that indicate the decision itself was mis-prioritized,
# as opposed to reasons that are execution-specific (e.g. no_time, external_blocker).
_DEPRIORITIZING_REASONS = {
    RejectionReason.NOT_PRIORITY.value,
    RejectionReason.ALREADY_RESOLVED.value,
}

DAMPENING_FACTOR = 0.85
MIN_SAMPLES = 2
REJECTION_RATE_THRESHOLD = 0.5


def _category_bucket(text: Optional[str]) -> Optional[str]:
    """Map a free-text category/type string to a known keyword bucket."""
    if not text:
        return None
    lowered = text.lower()
    for keyword in _CATEGORY_KEYWORDS:
        if keyword in lowered:
            return keyword
    return None


class ExecutionFeedbackService:
    """Aggregates confirmed execution results into a per-category dampening signal."""

    def compute_stats(self, records: Iterable[Any]) -> Dict[str, Dict[str, int]]:
        """
        Build per-bucket stats from execution records that reached a
        terminal, confirmed status.

        Returns: {bucket: {"total": int, "deprioritizing_rejections": int}}
        """
        stats: Dict[str, Dict[str, int]] = {}
        for record in records:
            confirmation = getattr(record, "confirmation", None)
            status = getattr(record, "current_status", None)
            if confirmation is None or status not in (
                DecisionStatus.COMPLETED,
                DecisionStatus.NOT_COMPLETED,
                DecisionStatus.PARTIAL,
            ):
                continue

            bucket = _category_bucket(getattr(record, "decision_category", None))
            if not bucket:
                continue

            entry = stats.setdefault(bucket, {"total": 0, "deprioritizing_rejections": 0})
            entry["total"] += 1

            rejection_reason = getattr(confirmation, "rejection_reason", None)
            reason_value = getattr(rejection_reason, "value", rejection_reason)
            if status == DecisionStatus.NOT_COMPLETED and reason_value in _DEPRIORITIZING_REASONS:
                entry["deprioritizing_rejections"] += 1

        return stats

    def dampening_for_text(self, text: Optional[str], stats: Dict[str, Dict[str, int]]) -> float:
        """
        Return the priority-score multiplier (0 < value <= 1) for a given
        risk_type/recovery_type/opportunity_type, based on precomputed stats.
        """
        bucket = _category_bucket(text)
        if not bucket or bucket not in stats:
            return 1.0

        entry = stats[bucket]
        total = entry["total"]
        if total < MIN_SAMPLES:
            return 1.0

        rejection_rate = entry["deprioritizing_rejections"] / total
        if rejection_rate >= REJECTION_RATE_THRESHOLD:
            logger.info(
                "ExecutionFeedbackService: dampening category '%s' "
                "(rejection_rate=%.2f over %d samples)",
                bucket, rejection_rate, total,
            )
            return DAMPENING_FACTOR
        return 1.0
