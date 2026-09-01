"""Tests for EXEC-03 — SQLExecutionRecordStore (real DB persistence, SQLite backend)."""

from decimal import Decimal

import pytest

from src.services.decision_execution.models import (
    DecisionAction,
    DecisionStatus,
    EstimatedImpact,
    ExecutionRecord,
    ExecutionTimeline,
    ImpactType,
)
from src.services.decision_execution.sql_store import SQLExecutionRecordStore


def _make_record(decision_id: str, status: DecisionStatus = DecisionStatus.NEW) -> ExecutionRecord:
    timeline = ExecutionTimeline(decision_id=decision_id, tenant_id="t1", empresa_codigo="1")
    return ExecutionRecord(
        decision_id=decision_id,
        tenant_id="t1",
        empresa_codigo="1",
        decision_title="Title",
        decision_category="CardReceivableDetector",
        decision_type="CardReceivableDetector",
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


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "execution_records.db"
    return SQLExecutionRecordStore(db_url=f"sqlite:///{db_path}")


def test_save_and_get_round_trips_record(store):
    record = _make_record("dec-sql-001")
    store.save(record)

    fetched = store.get("dec-sql-001")
    assert fetched is not None
    assert fetched.decision_id == "dec-sql-001"
    assert fetched.current_status == DecisionStatus.NEW
    assert fetched.estimated_impact.amount == Decimal("1000.00")


def test_get_returns_none_for_missing_decision(store):
    assert store.get("does-not-exist") is None


def test_save_upserts_existing_record(store):
    record = _make_record("dec-sql-002")
    store.save(record)

    record.current_status = DecisionStatus.EXECUTING
    store.save(record)

    fetched = store.get("dec-sql-002")
    assert fetched.current_status == DecisionStatus.EXECUTING
    assert len(store.list_all()) == 1


def test_update_applies_mutator_atomically(store):
    record = _make_record("dec-sql-003")
    store.save(record)

    def _mutator(rec: ExecutionRecord) -> ExecutionRecord:
        rec.current_status = DecisionStatus.COMPLETED
        return rec

    updated = store.update("dec-sql-003", _mutator)
    assert updated.current_status == DecisionStatus.COMPLETED
    assert store.get("dec-sql-003").current_status == DecisionStatus.COMPLETED


def test_update_raises_key_error_for_missing_decision(store):
    with pytest.raises(KeyError):
        store.update("missing", lambda rec: rec)


def test_list_all_returns_every_record(store):
    store.save(_make_record("dec-sql-004"))
    store.save(_make_record("dec-sql-005"))

    records = store.list_all()
    assert {r.decision_id for r in records} == {"dec-sql-004", "dec-sql-005"}
