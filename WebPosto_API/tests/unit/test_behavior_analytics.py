"""Tests for FASE 5 (APRENDER) — BehaviorAnalyticsService."""

from datetime import datetime
from decimal import Decimal

from src.services.decision_execution.behavior_analytics import BehaviorAnalyticsService
from src.services.decision_execution.models import (
    ConfirmationResult,
    DecisionAction,
    DecisionStatus,
    EstimatedImpact,
    ExecutionRecord,
    ExecutionTimeline,
    ImpactType,
    RejectionReason,
    ResultConfirmation,
)


def _make_record(decision_id: str, category: str, status: DecisionStatus, rejection_reason=None):
    timeline = ExecutionTimeline(decision_id=decision_id, tenant_id="t1", empresa_codigo="1")
    record = ExecutionRecord(
        decision_id=decision_id,
        tenant_id="t1",
        empresa_codigo="1",
        decision_title="Title",
        decision_category=category,
        decision_type=category,
        priority="high",
        current_status=status,
        timeline=timeline,
        estimated_impact=EstimatedImpact(
            impact_type=ImpactType.RECOVERED,
            amount=Decimal("1000.00"),
            confidence=0.8,
            calculation_method="test",
            source_engine="test",
        ),
        confidence_score=80.0,
        source_engine="test",
        action_type=DecisionAction.EXECUTE_NOW,
    )
    if status != DecisionStatus.NEW:
        record.confirmation = ResultConfirmation(
            decision_id=decision_id,
            tenant_id="t1",
            empresa_codigo="1",
            result=(
                ConfirmationResult.NO
                if status == DecisionStatus.NOT_COMPLETED
                else ConfirmationResult.YES
            ),
            confirmed_by="owner",
            confirmed_at=datetime.utcnow(),
            verification_method="owner_confirmed",
            rejection_reason=rejection_reason,
        )
    return record


def test_analyze_returns_empty_report_for_no_records():
    insights = BehaviorAnalyticsService().analyze([])
    assert insights["categories"] == {}
    assert insights["most_executed_category"] is None
    assert insights["most_ignored_category"] is None
    assert insights["top_rejection_reasons"] == {}


def test_analyze_tracks_executed_vs_ignored_categories():
    records = [
        _make_record("d1", "CardReceivableDetector", DecisionStatus.COMPLETED),
        _make_record("d2", "CardReceivableDetector", DecisionStatus.COMPLETED),
        _make_record(
            "d3",
            "ExpenseDetector",
            DecisionStatus.NOT_COMPLETED,
            rejection_reason=RejectionReason.NOT_PRIORITY,
        ),
        _make_record("d4", "ExpenseDetector", DecisionStatus.EXPIRED),
        _make_record("d5", "RevenueDetector", DecisionStatus.NEW),
    ]

    insights = BehaviorAnalyticsService().analyze(records)

    card_stats = insights["categories"]["CardReceivableDetector"]
    assert card_stats["presented"] == 2
    assert card_stats["executed"] == 2
    assert card_stats["completed"] == 2
    assert card_stats["execution_rate"] == 100.0
    assert card_stats["completion_rate"] == 100.0

    expense_stats = insights["categories"]["ExpenseDetector"]
    assert expense_stats["not_completed"] == 1
    assert expense_stats["expired"] == 1
    assert expense_stats["rejection_reasons"][RejectionReason.NOT_PRIORITY.value] == 1

    # RevenueDetector is NEW (never presented) -> should not count as presented/executed
    revenue_stats = insights["categories"]["RevenueDetector"]
    assert revenue_stats["presented"] == 0
    assert revenue_stats["executed"] == 0

    assert insights["most_executed_category"] == "CardReceivableDetector"
    assert insights["most_ignored_category"] == "ExpenseDetector"
    assert insights["top_rejection_reasons"][RejectionReason.NOT_PRIORITY.value] == 1
