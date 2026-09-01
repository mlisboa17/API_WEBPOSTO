"""
Behavior Analytics Service — FASE 5 (APRENDER), sprint "Behavior Learning".

Analyzes the owner's confirmed execution history (ExecutionRecord) to answer:
- Which decision categories does the owner consistently execute?
- Which does the owner ignore (expire without action) or reject?
- What are the most common rejection reasons, overall and per category?
- How long does the owner typically take to act on each category?

This is purely descriptive/analytical (read-only reporting) — it does not
change behavior by itself. The EXEC-03 ExecutionFeedbackService already
consumes a similar signal to softly dampen priority scores; this service
is the human-facing report version, broken down per real decision_category
(no keyword bridging needed, since this only serves the execution history
UI/report, not the owner_intelligence "Motor 4" scoring pipeline).
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from .models import DecisionStatus

_EXECUTED_STATUSES = {
    DecisionStatus.EXECUTING,
    DecisionStatus.COMPLETED,
    DecisionStatus.NOT_COMPLETED,
    DecisionStatus.PARTIAL,
}
_TERMINAL_STATUSES = {
    DecisionStatus.COMPLETED,
    DecisionStatus.NOT_COMPLETED,
    DecisionStatus.PARTIAL,
}
_IGNORED_STATUSES = {DecisionStatus.EXPIRED}


def _empty_category_stats() -> Dict[str, Any]:
    return {
        "presented": 0,
        "executed": 0,
        "completed": 0,
        "not_completed": 0,
        "partial": 0,
        "expired": 0,
        "rejection_reasons": {},
        "_time_to_execute_samples": [],
    }


class BehaviorAnalyticsService:
    """Turns raw ExecutionRecord history into owner behavior insights."""

    def analyze(self, records: Iterable[Any]) -> Dict[str, Any]:
        categories: Dict[str, Dict[str, Any]] = {}
        top_rejection_reasons: Dict[str, int] = {}

        for record in records:
            category = getattr(record, "decision_category", None) or "unknown"
            status = getattr(record, "current_status", None)
            stats = categories.setdefault(category, _empty_category_stats())

            if status != DecisionStatus.NEW:
                stats["presented"] += 1

            if status in _EXECUTED_STATUSES:
                stats["executed"] += 1

            if status == DecisionStatus.COMPLETED:
                stats["completed"] += 1
            elif status == DecisionStatus.NOT_COMPLETED:
                stats["not_completed"] += 1
            elif status == DecisionStatus.PARTIAL:
                stats["partial"] += 1
            elif status == DecisionStatus.EXPIRED:
                stats["expired"] += 1

            confirmation = getattr(record, "confirmation", None)
            rejection_reason = (
                getattr(confirmation, "rejection_reason", None) if confirmation else None
            )
            reason_value = getattr(rejection_reason, "value", rejection_reason)
            if reason_value:
                stats["rejection_reasons"][reason_value] = (
                    stats["rejection_reasons"].get(reason_value, 0) + 1
                )
                top_rejection_reasons[reason_value] = top_rejection_reasons.get(reason_value, 0) + 1

            if status in _TERMINAL_STATUSES:
                get_time_to_execute = getattr(record, "get_time_to_execute", None)
                delta = get_time_to_execute() if callable(get_time_to_execute) else None
                if delta is not None:
                    stats["_time_to_execute_samples"].append(delta.total_seconds() / 60)

        category_report: Dict[str, Any] = {}
        for category, stats in categories.items():
            samples = stats.pop("_time_to_execute_samples")
            executed = stats["executed"]
            terminal = stats["completed"] + stats["not_completed"] + stats["partial"]
            stats["execution_rate"] = (
                round((executed / stats["presented"]) * 100, 1) if stats["presented"] else 0.0
            )
            stats["completion_rate"] = (
                round((stats["completed"] / terminal) * 100, 1) if terminal else 0.0
            )
            stats["avg_time_to_execute_minutes"] = (
                round(sum(samples) / len(samples), 1) if samples else None
            )
            category_report[category] = stats

        most_executed_category = self._pick_extreme(category_report, key="executed", reverse=True)
        most_ignored_category = self._pick_extreme(
            category_report,
            key=lambda s: s["expired"] + s["not_completed"],
            reverse=True,
        )

        return {
            "categories": category_report,
            "most_executed_category": most_executed_category,
            "most_ignored_category": most_ignored_category,
            "top_rejection_reasons": dict(
                sorted(top_rejection_reasons.items(), key=lambda kv: kv[1], reverse=True)
            ),
        }

    @staticmethod
    def _pick_extreme(
        category_report: Dict[str, Dict[str, Any]], key, reverse: bool
    ) -> Optional[str]:
        if not category_report:
            return None
        keyfn = key if callable(key) else (lambda s: s[key])
        best_category, best_stats = (
            max(category_report.items(), key=lambda kv: keyfn(kv[1]))
            if reverse
            else min(category_report.items(), key=lambda kv: keyfn(kv[1]))
        )
        return best_category if keyfn(best_stats) > 0 else None
