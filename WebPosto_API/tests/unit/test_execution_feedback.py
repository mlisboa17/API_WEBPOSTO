"""Tests for EXEC-03 — ExecutionFeedbackService (Owner Intelligence integration)."""

from datetime import datetime
from decimal import Decimal

import pytest

from src.services.decision_execution.feedback import ExecutionFeedbackService
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
from src.services.owner_intelligence.daily_actions import DailyActionsEngine
from src.services.owner_intelligence.priority_engine import PriorityEngine
from src.services.owner_intelligence.schemas import ActionPriority, ActionType


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
    record.confirmation = ResultConfirmation(
        decision_id=decision_id,
        tenant_id="t1",
        empresa_codigo="1",
        result=ConfirmationResult.NO if status == DecisionStatus.NOT_COMPLETED else ConfirmationResult.YES,
        confirmed_by="owner",
        confirmed_at=datetime.utcnow(),
        verification_method="owner_confirmed",
        rejection_reason=rejection_reason,
    )
    return record


def test_compute_stats_ignores_records_without_confirmation():
    record = _make_record("d1", "CardReceivableDetector", DecisionStatus.EXECUTING)
    record.confirmation = None
    stats = ExecutionFeedbackService().compute_stats([record])
    assert stats == {}


def test_dampening_triggers_after_repeated_not_priority_rejections():
    records = [
        _make_record("d1", "CardReceivableDetector", DecisionStatus.NOT_COMPLETED, RejectionReason.NOT_PRIORITY),
        _make_record("d2", "CardReceivableDetector", DecisionStatus.NOT_COMPLETED, RejectionReason.NOT_PRIORITY),
        _make_record("d3", "ExpenseDetector", DecisionStatus.COMPLETED),
    ]
    feedback = ExecutionFeedbackService()
    stats = feedback.compute_stats(records)

    assert feedback.dampening_for_text("card_reconciliation", stats) == pytest.approx(0.85)
    assert feedback.dampening_for_text("expense_increase", stats) == 1.0
    assert feedback.dampening_for_text(None, stats) == 1.0
    assert feedback.dampening_for_text("revenue_decline", stats) == 1.0


def test_dampening_requires_minimum_samples():
    records = [
        _make_record("d1", "CardReceivableDetector", DecisionStatus.NOT_COMPLETED, RejectionReason.NOT_PRIORITY),
    ]
    feedback = ExecutionFeedbackService()
    stats = feedback.compute_stats(records)
    assert feedback.dampening_for_text("card_reconciliation", stats) == 1.0


def test_priority_engine_applies_dampening_multiplier():
    engine = PriorityEngine()
    base = engine.calculate_score(
        financial_value=10000,
        urgency_score=0.8,
        confidence=0.9,
        action_type=ActionType.RECOVER,
        priority=ActionPriority.HIGH,
        time_to_resolve=30,
    )
    dampened = engine.calculate_score(
        financial_value=10000,
        urgency_score=0.8,
        confidence=0.9,
        action_type=ActionType.RECOVER,
        priority=ActionPriority.HIGH,
        time_to_resolve=30,
        dampening_multiplier=0.85,
    )
    assert dampened["total_score"] < base["total_score"]
    assert dampened["total_score"] == pytest.approx(base["total_score"] * 0.85, rel=1e-2)


def test_daily_actions_engine_category_text_extraction():
    class FakeFinding:
        risk_type = "card_reconciliation"

    class FakeAction:
        pass

    from src.services.owner_intelligence.daily_actions import RawDecisionCandidate

    candidate = RawDecisionCandidate(
        source_type="risk",
        source_finding=FakeFinding(),
        action=FakeAction(),
        financial_value=100.0,
        urgency_score=0.5,
        confidence_score=0.8,
    )
    assert DailyActionsEngine._category_text(candidate) == "card_reconciliation"
