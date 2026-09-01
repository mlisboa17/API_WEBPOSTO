"""Unit tests for the Preference Model Service."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.services.decision_execution.efficacy_analytics import (
    CategoryEfficacy,
    EfficacyAnalyticsEngine,
)
from src.services.decision_execution.preference_model import (
    PreferenceModelService,
    PreferenceWeightResult,
)
from src.services.owner_intelligence.schemas import (
    ActionPriority,
    ActionStatus,
    ActionType,
    ConfidenceLevel,
    DailyDecision,
    DecisionAction,
    DecisionSource,
    FinancialImpact,
)


def _make_source() -> DecisionSource:
    return DecisionSource(
        endpoint="/test",
        service="TestService",
        method="test",
        data_timestamp=datetime.now(timezone.utc),
    )


def _make_financial_impact() -> FinancialImpact:
    return FinancialImpact(
        estimated_value=1000.0,
        currency="BRL",
        impact_type="recoverable",
        probability=0.8,
        timeframe_days=7,
    )


def _make_action(
    priority: ActionPriority = ActionPriority.HIGH, category: str = "price"
) -> DecisionAction:
    return DecisionAction(
        id=f"act_{priority}_{category}",
        type=ActionType.REVIEW,
        priority=priority,
        status=ActionStatus.PENDING,
        title="Action",
        description="Action description",
        financial_impact=_make_financial_impact(),
        source=_make_source(),
        confidence=0.85,
        confidence_level=ConfidenceLevel.HIGH,
        tenant_id="t1",
        empresa_codigo="123",
        suggested_action="Execute",
        category=category,
    )


def _make_decision(
    decision_id: str,
    total_score: float,
    rank: int = 1,
    priority: ActionPriority = ActionPriority.HIGH,
    category: str = "price",
) -> DailyDecision:
    return DailyDecision(
        id=decision_id,
        rank=rank,
        title="Decision",
        description="Description",
        decision_question="Question?",
        why_appeared="Why",
        why_ranked="Why ranked",
        money_involved="Money",
        what_rule_triggered="Rule",
        total_score=total_score,
        financial_impact_score=50.0,
        urgency_score=50.0,
        confidence_score=50.0,
        ease_score=50.0,
        time_score=50.0,
        action=_make_action(priority=priority, category=category),
        decision_type="risk",
    )


def _make_engine(preference_scores: dict[str, float]) -> EfficacyAnalyticsEngine:
    engine = EfficacyAnalyticsEngine.__new__(EfficacyAnalyticsEngine)
    engine._store = MagicMock()
    engine._ttl = MagicMock()
    engine._cache = {}
    engine._cache_lock = MagicMock()

    def calculate(tenant_id: str, empresa_codigo: str) -> dict[str, CategoryEfficacy]:
        return {
            category: CategoryEfficacy(
                category=category,
                presented=10,
                executed=5,
                completed=4,
                not_completed=1,
                partial=0,
                expired=0,
                success_rate=80.0,
                execution_rate=50.0,
                rejection_rate=20.0,
                efficacy_score=0.8,
                preference_score=score,
            )
            for category, score in preference_scores.items()
        }

    setattr(engine, "calculate", calculate)
    return engine


class TestPreferenceModelService:
    def test_apply_preference_weights_boosts_high_preference_category(self):
        engine = _make_engine({"price": 1.0, "margin": 0.0})
        service = PreferenceModelService(engine)
        decisions = [
            _make_decision("d1", total_score=80.0, rank=1, category="margin"),
            _make_decision("d2", total_score=80.0, rank=2, category="price"),
        ]

        adjusted, _ = service.apply_preference_weights(decisions, "t1", "123")

        price = next(d for d in adjusted if d.id == "d2")
        margin = next(d for d in adjusted if d.id == "d1")
        assert price.total_score == pytest.approx(92.0, rel=1e-3)
        assert margin.total_score == pytest.approx(68.0, rel=1e-3)
        assert adjusted[0].id == "d2"

    def test_critical_decision_never_reduced(self):
        engine = _make_engine({"margin": 0.0})
        service = PreferenceModelService(engine)
        decisions = [
            _make_decision(
                "d1", total_score=80.0, priority=ActionPriority.CRITICAL, category="margin"
            )
        ]

        adjusted, audit = service.apply_preference_weights(decisions, "t1", "123")

        assert adjusted[0].total_score == pytest.approx(92.0, rel=1e-3)
        assert audit[0].reason == "critical priority protected from reduction (category=margin)"

    def test_critical_decision_can_be_boosted_above_cap(self):
        engine = _make_engine({"price": 1.0})
        service = PreferenceModelService(engine)
        decisions = [
            _make_decision(
                "d1", total_score=80.0, priority=ActionPriority.CRITICAL, category="price"
            )
        ]

        adjusted, _ = service.apply_preference_weights(decisions, "t1", "123")

        assert adjusted[0].total_score == pytest.approx(92.0, rel=1e-3)

    def test_multiplier_bounded_within_range(self):
        # Simulate extreme preference score still maps to [0.85, 1.15]
        engine = _make_engine({"loyalty": 1.0})
        service = PreferenceModelService(engine)
        decisions = [_make_decision("d1", total_score=100.0, category="loyalty")]

        adjusted, _ = service.apply_preference_weights(decisions, "t1", "123")

        assert adjusted[0].total_score == pytest.approx(100.0, rel=1e-3)

    def test_unknown_category_gets_neutral_multiplier(self):
        engine = _make_engine({"other": 0.5})
        service = PreferenceModelService(engine)
        decisions = [_make_decision("d1", total_score=80.0, category="unknown")]

        adjusted, _ = service.apply_preference_weights(decisions, "t1", "123")

        assert adjusted[0].total_score == pytest.approx(80.0, rel=1e-3)

    def test_re_ranking_after_adjustment(self):
        engine = _make_engine({"price": 1.0, "margin": 0.0})
        service = PreferenceModelService(engine)
        decisions = [
            _make_decision("d1", total_score=82.0, rank=1, category="margin"),
            _make_decision("d2", total_score=80.0, rank=2, category="price"),
        ]

        adjusted, _ = service.apply_preference_weights(decisions, "t1", "123")

        assert adjusted[0].id == "d2"
        assert adjusted[0].rank == 1
        assert adjusted[1].id == "d1"
        assert adjusted[1].rank == 2

    def test_returned_audit_matches_adjustments(self):
        engine = _make_engine({"price": 0.5})
        service = PreferenceModelService(engine)
        decisions = [_make_decision("d1", total_score=80.0, category="price")]

        adjusted, audit = service.apply_preference_weights(decisions, "t1", "123")

        assert isinstance(audit[0], PreferenceWeightResult)
        assert audit[0].decision_id == "d1"
        assert audit[0].original_score == 80.0
        assert audit[0].adjusted_score == adjusted[0].total_score
        assert audit[0].multiplier == pytest.approx(1.0, rel=1e-3)
