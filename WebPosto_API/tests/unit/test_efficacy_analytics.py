"""Tests for FASE 5 (APRENDER) — EfficacyAnalyticsEngine."""

from datetime import timedelta
from decimal import Decimal

import pytest

from src.services.decision_execution.efficacy_analytics import EfficacyAnalyticsEngine
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
from src.services.decision_execution.sql_store import SQLExecutionRecordStore


def _make_record(
    decision_id: str,
    category: str,
    status: DecisionStatus,
    tenant_id: str = "t1",
    empresa_codigo: str = "1",
) -> ExecutionRecord:
    timeline = ExecutionTimeline(
        decision_id=decision_id, tenant_id=tenant_id, empresa_codigo=empresa_codigo
    )
    record = ExecutionRecord(
        decision_id=decision_id,
        tenant_id=tenant_id,
        empresa_codigo=empresa_codigo,
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
            tenant_id=tenant_id,
            empresa_codigo=empresa_codigo,
            result=(
                ConfirmationResult.NO
                if status == DecisionStatus.NOT_COMPLETED
                else ConfirmationResult.YES
            ),
            confirmed_by="owner",
            verification_method="owner_confirmed",
            rejection_reason=(
                RejectionReason.NOT_PRIORITY if status == DecisionStatus.NOT_COMPLETED else None
            ),
        )
    return record


@pytest.fixture
def engine(tmp_path):
    store = SQLExecutionRecordStore(db_url=f"sqlite:///{tmp_path}/efficacy.db")
    return EfficacyAnalyticsEngine(store=store, ttl_seconds=60.0)


def test_empty_store_returns_empty(engine):
    result = engine.calculate("t1", "1")
    assert result == {}


def test_new_records_are_excluded_from_presented(engine):
    engine._store.save(_make_record("d1", "CatA", DecisionStatus.NEW))
    result = engine.calculate("t1", "1")
    assert result == {}


def test_success_rate_and_rejection_rate(engine):
    engine._store.save(_make_record("d1", "CatA", DecisionStatus.COMPLETED))
    engine._store.save(_make_record("d2", "CatA", DecisionStatus.COMPLETED))
    engine._store.save(_make_record("d3", "CatA", DecisionStatus.NOT_COMPLETED))

    result = engine.calculate("t1", "1")
    cat = result["CatA"]
    assert cat.presented == 3
    assert cat.executed == 3
    assert cat.completed == 2
    assert cat.not_completed == 1
    assert cat.success_rate == pytest.approx(66.7, abs=0.1)
    assert cat.rejection_rate == pytest.approx(33.3, abs=0.1)
    assert cat.execution_rate == 100.0
    assert cat.efficacy_score == pytest.approx(0.667, abs=0.001)


def test_preference_score_reflects_relative_success(engine):
    engine._store.save(_make_record("d1", "CatA", DecisionStatus.COMPLETED))
    engine._store.save(_make_record("d2", "CatA", DecisionStatus.NOT_COMPLETED))
    engine._store.save(_make_record("d3", "CatB", DecisionStatus.COMPLETED))

    result = engine.calculate("t1", "1")
    cat_a = result["CatA"]
    cat_b = result["CatB"]

    assert cat_b.success_rate == 100.0
    assert cat_a.success_rate == 50.0
    assert cat_b.preference_score > cat_a.preference_score
    assert 0.0 < cat_a.preference_score < 1.0
    assert 0.0 < cat_b.preference_score < 1.0


def test_tenant_isolation(engine):
    engine._store.save(
        _make_record("d1", "CatA", DecisionStatus.COMPLETED, tenant_id="t1", empresa_codigo="1")
    )
    engine._store.save(
        _make_record("d2", "CatA", DecisionStatus.NOT_COMPLETED, tenant_id="t2", empresa_codigo="2")
    )

    t1 = engine.calculate("t1", "1")
    t2 = engine.calculate("t2", "2")

    assert t1["CatA"].success_rate == 100.0
    assert t2["CatA"].success_rate == 0.0


def test_cache_returns_stale_value_while_valid(engine):
    engine._store.save(_make_record("d1", "CatA", DecisionStatus.COMPLETED))
    first = engine.calculate("t1", "1")

    engine._store.save(_make_record("d2", "CatA", DecisionStatus.NOT_COMPLETED))
    second = engine.calculate("t1", "1")

    assert second is first
    assert second["CatA"].success_rate == 100.0


def test_cache_expires_after_ttl(engine):
    engine._store.save(_make_record("d1", "CatA", DecisionStatus.COMPLETED))
    engine.calculate("t1", "1")

    engine._store.save(_make_record("d2", "CatA", DecisionStatus.NOT_COMPLETED))

    with engine._cache_lock:
        cached_at, _ = engine._cache[("t1", "1")]
        engine._cache[("t1", "1")] = (cached_at - timedelta(seconds=120), {})

    result = engine.calculate("t1", "1")
    assert result["CatA"].success_rate == 50.0


def test_partial_counts_as_terminal_but_not_success(engine):
    engine._store.save(_make_record("d1", "CatA", DecisionStatus.COMPLETED))
    engine._store.save(_make_record("d2", "CatA", DecisionStatus.PARTIAL))

    result = engine.calculate("t1", "1")
    cat = result["CatA"]
    assert cat.partial == 1
    assert cat.success_rate == 50.0
    assert cat.execution_rate == 100.0


def test_expired_does_not_count_as_executed(engine):
    engine._store.save(_make_record("d1", "CatA", DecisionStatus.READY))
    engine._store.save(_make_record("d2", "CatA", DecisionStatus.EXPIRED))

    result = engine.calculate("t1", "1")
    cat = result["CatA"]
    assert cat.presented == 2
    assert cat.executed == 0
    assert cat.expired == 1
    assert cat.execution_rate == 0.0


def test_clear_cache_removes_cached_values(engine):
    engine._store.save(_make_record("d1", "CatA", DecisionStatus.COMPLETED))
    engine.calculate("t1", "1")
    engine.clear_cache()

    engine._store.save(_make_record("d2", "CatA", DecisionStatus.NOT_COMPLETED))
    result = engine.calculate("t1", "1")
    assert result["CatA"].success_rate == 50.0
