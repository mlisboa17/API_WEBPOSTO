"""EXEC-02 — testes dos endpoints de execução de decisão (execute/confirm/timeline).

Usa store JSON isolado em diretório temporário (nunca o snapshots/ real) e
monkeypatch em DecisionEvidenceService.get_evidence para simular o snapshot
DIR-01 sem depender de dados reais.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest

from src.interfaces.http.routes import decisions as mod
from src.services.decision_evidence.models import DecisionEvidenceResponse
from src.services.decision_execution import ExecutionRecordStore, ExecutionService
from src.services.owner_intelligence.schemas import (
    ActionPriority,
    ActionType,
    BusinessHealthMetrics,
    ConfidenceLevel,
    DailyDecision,
    DecisionAction,
    DecisionSource,
    FinancialImpact,
    OwnerActionCenterSummary,
)


def _fake_evidence(decision_id: str, *, recoverable: float = 8500.0) -> DecisionEvidenceResponse:
    return DecisionEvidenceResponse(
        decision_id=decision_id,
        decision_summary="Cobrar cliente inadimplente",
        root_cause="teste",
        money_found={
            "at_risk": {"value": 0, "type": "estimated"},
            "recoverable": {"value": recoverable, "type": "estimated"},
            "additional": {"value": 0, "type": "estimated"},
        },
        confidence=0.9,
        evidence_items=[],
        evidence_items_count=0,
        evidence_items_total=0,
        limitations=[],
        source_metadata={
            "detector": "CardReceivableDetector",
            "tenant_id": "74014",
            "tenant_name": "Posto Doze",
            "source_endpoints": ["/INTEGRACAO/CARTAO"],
        },
    )


@pytest.fixture()
def isolated_store(tmp_path, monkeypatch):
    store = ExecutionRecordStore(store_path=tmp_path / "store.json")
    service = ExecutionService(repository=store)
    monkeypatch.setattr(mod, "_execution_store", store)
    monkeypatch.setattr(mod, "_execution_service", service)
    return store


def test_execute_unknown_decision_returns_404(isolated_store, monkeypatch):
    async def _none(*_a, **_kw):
        return None

    monkeypatch.setattr(mod._evidence_service, "get_evidence", _none)

    with pytest.raises(Exception) as exc_info:
        asyncio.run(mod.execute_decision_endpoint("nao-existe", mod.ExecuteDecisionBody()))
    assert getattr(exc_info.value, "status_code", None) == 404


def test_execute_then_confirm_yes_completes_with_confirmed_impact(isolated_store, monkeypatch):
    async def _get(decision_id, **_kw):
        return _fake_evidence(decision_id)

    monkeypatch.setattr(mod._evidence_service, "get_evidence", _get)

    exec_result = asyncio.run(mod.execute_decision_endpoint("dec-001", mod.ExecuteDecisionBody()))
    assert exec_result["data"]["estimated_impact"]["amount"] == 8500.0
    assert exec_result["data"]["estimated_impact"]["label"] == "ESTIMADO"

    confirm_result = asyncio.run(
        mod.confirm_decision_endpoint(
            "dec-001", mod.ConfirmDecisionBody(result="yes", confirmed_amount=8200.0)
        )
    )
    data = confirm_result["data"]
    assert data["status"] == "completed"
    assert data["confirmed_impact"]["label"] == "CONFIRMADO"
    assert data["confirmed_impact"]["amount"] == 8200.0

    timeline_result = asyncio.run(mod.get_decision_timeline("dec-001"))
    statuses = [e["status"] for e in timeline_result["data"]["timeline"]]
    assert statuses == ["new", "ready", "executing", "completed"]


def test_confirm_no_marks_not_completed_with_rejection_reason(isolated_store, monkeypatch):
    async def _get(decision_id, **_kw):
        return _fake_evidence(decision_id)

    monkeypatch.setattr(mod._evidence_service, "get_evidence", _get)

    asyncio.run(mod.execute_decision_endpoint("dec-002", mod.ExecuteDecisionBody()))
    confirm_result = asyncio.run(
        mod.confirm_decision_endpoint(
            "dec-002",
            mod.ConfirmDecisionBody(result="no", rejection_reason="no_time"),
        )
    )
    assert confirm_result["data"]["status"] == "not_completed"
    assert "confirmed_impact" not in confirm_result["data"]


def test_confirm_before_execute_returns_404(isolated_store, monkeypatch):
    with pytest.raises(Exception) as exc_info:
        asyncio.run(
            mod.confirm_decision_endpoint(
                "dec-never-executed", mod.ConfirmDecisionBody(result="yes", confirmed_amount=1.0)
            )
        )
    assert getattr(exc_info.value, "status_code", None) == 404


def test_execute_is_idempotent_while_executing(isolated_store, monkeypatch):
    async def _get(decision_id, **_kw):
        return _fake_evidence(decision_id)

    monkeypatch.setattr(mod._evidence_service, "get_evidence", _get)

    asyncio.run(mod.execute_decision_endpoint("dec-003", mod.ExecuteDecisionBody()))
    second = asyncio.run(mod.execute_decision_endpoint("dec-003", mod.ExecuteDecisionBody()))
    assert second["data"]["status"] == "executing"


def test_metrics_summary_reflects_pending_and_confirmed_decisions(isolated_store, monkeypatch):
    async def _get(decision_id, **_kw):
        return _fake_evidence(decision_id)

    monkeypatch.setattr(mod._evidence_service, "get_evidence", _get)

    asyncio.run(mod.execute_decision_endpoint("dec-004", mod.ExecuteDecisionBody()))
    asyncio.run(
        mod.confirm_decision_endpoint(
            "dec-004", mod.ConfirmDecisionBody(result="yes", confirmed_amount=8200.0)
        )
    )

    result = asyncio.run(
        mod.get_execution_metrics_summary(tenant_id="74014", empresa_codigo="74014")
    )
    data = result["data"]
    assert data["tenant_id"] == "74014"
    assert data["total_completed"] >= 1
    assert data["total_confirmed_value"] >= 8200.0


def test_metrics_period_computes_execution_rates(isolated_store, monkeypatch):
    from datetime import datetime, timedelta

    async def _get(decision_id, **_kw):
        return _fake_evidence(decision_id)

    monkeypatch.setattr(mod._evidence_service, "get_evidence", _get)

    asyncio.run(mod.execute_decision_endpoint("dec-005", mod.ExecuteDecisionBody()))
    asyncio.run(
        mod.confirm_decision_endpoint(
            "dec-005", mod.ConfirmDecisionBody(result="yes", confirmed_amount=8200.0)
        )
    )

    period_start = datetime.utcnow() - timedelta(days=1)
    period_end = datetime.utcnow() + timedelta(days=1)
    result = asyncio.run(
        mod.get_execution_metrics_period(period_start=period_start, period_end=period_end)
    )
    data = result["data"]
    assert data["decisions_generated"] >= 1
    assert data["decisions_completed"] >= 1
    assert data["execution_rate"] > 0
    assert data["completion_rate"] > 0


def test_behavior_insights_reports_executed_and_rejected_categories(isolated_store, monkeypatch):
    async def _get(decision_id, **_kw):
        return _fake_evidence(decision_id)

    monkeypatch.setattr(mod._evidence_service, "get_evidence", _get)

    asyncio.run(mod.execute_decision_endpoint("dec-006", mod.ExecuteDecisionBody()))
    asyncio.run(
        mod.confirm_decision_endpoint(
            "dec-006", mod.ConfirmDecisionBody(result="yes", confirmed_amount=8200.0)
        )
    )

    result = asyncio.run(mod.get_behavior_insights())
    data = result["data"]
    assert "CardReceivableDetector" in data["categories"]
    assert data["categories"]["CardReceivableDetector"]["completed"] >= 1
    assert data["most_executed_category"] == "CardReceivableDetector"


# ---------------------------------------------------------------------------
# FASE 5 (APRENDER) — Action Center Top 5 with preference weights
# ---------------------------------------------------------------------------


def _make_decision_action(
    decision_id: str,
    priority: ActionPriority,
    category: str,
    tenant_id: str,
    empresa_codigo: str,
) -> DecisionAction:
    return DecisionAction(
        id=f"act-{decision_id}",
        type=ActionType.URGENT,
        priority=priority,
        title=f"Action {decision_id}",
        description="Test action",
        financial_impact=FinancialImpact(
            estimated_value=1000.0,
            impact_type="recoverable",
            probability=0.8,
            timeframe_days=1,
        ),
        source=DecisionSource(
            endpoint="/test",
            service="TestService",
            data_timestamp=datetime.utcnow(),
        ),
        confidence=0.85,
        confidence_level=ConfidenceLevel.HIGH,
        tenant_id=tenant_id,
        empresa_codigo=empresa_codigo,
        suggested_action="Execute",
        category=category,
    )


def _make_daily_decision(
    decision_id: str,
    rank: int,
    priority: ActionPriority,
    category: str,
    total_score: float,
    tenant_id: str = "tenant-001",
    empresa_codigo: str = "empresa-001",
) -> DailyDecision:
    action = _make_decision_action(decision_id, priority, category, tenant_id, empresa_codigo)
    return DailyDecision(
        id=decision_id,
        rank=rank,
        title=f"Decision {decision_id}",
        description="Test decision",
        decision_question="Should we act?",
        why_appeared="Test",
        why_ranked="Test",
        money_involved="R$ 1.000,00",
        what_rule_triggered="test-rule",
        total_score=total_score,
        financial_impact_score=80.0,
        urgency_score=80.0,
        confidence_score=85.0,
        ease_score=80.0,
        time_score=80.0,
        action=action,
        decision_type="recovery",
    )


def _make_owner_summary(
    tenant_id: str,
    empresa_codigo: str,
    decisions: list[DailyDecision],
    preference_audit: list[dict] | None = None,
) -> OwnerActionCenterSummary:
    now = datetime.utcnow()
    return OwnerActionCenterSummary(
        tenant_id=tenant_id,
        empresa_codigo=empresa_codigo,
        generated_at=now,
        data_period_start=now - timedelta(days=30),
        data_period_end=now,
        business_health=BusinessHealthMetrics(
            score=70.0,
            status="good",
            trend="stable",
            trend_percent=0.0,
            revenue_health=70.0,
            expense_health=70.0,
            cash_health=70.0,
            margin_health=70.0,
            operational_health=70.0,
            summary="Test summary",
            recommendations=[],
        ),
        money_at_risk=[],
        money_at_risk_total=0,
        recoverable_money=[],
        recoverable_total=0,
        opportunities=[],
        opportunity_total=0,
        top_5_decisions=decisions,
        all_decisions=decisions,
        executive_summary="Test executive summary",
        greeting="Bom dia",
        total_actions=len(decisions),
        critical_actions=sum(1 for d in decisions if d.action.priority == ActionPriority.CRITICAL),
        high_actions=sum(1 for d in decisions if d.action.priority == ActionPriority.HIGH),
        actions_requiring_immediate_attention=0,
        confidence_average=0.85,
        data_sources=[],
        preference_audit=preference_audit or [],
    )


def test_top5_requires_tenant_and_company():
    with pytest.raises(Exception) as exc_info:
        asyncio.run(mod.get_top5_decisions(tenant_id="", empresa_codigo="123"))
    assert getattr(exc_info.value, "status_code", None) == 422


def test_top5_returns_empty_when_no_decisions(monkeypatch):
    async def _empty_summary(*_a, **_kw):
        return _make_owner_summary("tenant-001", "empresa-001", [])

    monkeypatch.setattr(
        mod._owner_intelligence_engine, "generate_action_center_summary", _empty_summary
    )

    result = asyncio.run(
        mod.get_top5_decisions(tenant_id="tenant-001", empresa_codigo="empresa-001")
    )
    assert result["success"] is True
    assert result["data"]["decisions"] == []
    assert result["data"]["preference_audit"] == []
    assert result["data"]["tenant_id"] == "tenant-001"
    assert result["data"]["empresa_codigo"] == "empresa-001"


def test_top5_returns_decisions_with_preference_audit(monkeypatch):
    decisions = [
        _make_daily_decision("dec-001", 1, ActionPriority.HIGH, "revenue", 90.0),
        _make_daily_decision("dec-002", 2, ActionPriority.HIGH, "expense", 80.0),
    ]
    audit = [
        {
            "decision_id": "dec-001",
            "category": "revenue",
            "original_score": 90.0,
            "adjusted_score": 94.5,
            "multiplier": 1.05,
            "reason": "positive preference bias",
        },
        {
            "decision_id": "dec-002",
            "category": "expense",
            "original_score": 80.0,
            "adjusted_score": 76.0,
            "multiplier": 0.95,
            "reason": "negative preference bias",
        },
    ]

    async def _summary(*_a, **_kw):
        return _make_owner_summary("tenant-001", "empresa-001", decisions, audit)

    monkeypatch.setattr(mod._owner_intelligence_engine, "generate_action_center_summary", _summary)

    result = asyncio.run(
        mod.get_top5_decisions(tenant_id="tenant-001", empresa_codigo="empresa-001")
    )
    data = result["data"]
    assert len(data["decisions"]) == 2
    assert data["decisions"][0]["id"] == "dec-001"
    assert data["total_actions"] == 2
    assert len(data["preference_audit"]) == 2
    assert data["preference_audit"][0]["decision_id"] == "dec-001"
    assert "multiplier" in data["preference_audit"][0]
    assert "reason" in data["preference_audit"][0]


def test_top5_critical_decision_never_reduced(monkeypatch):
    decisions = [
        _make_daily_decision("dec-critical", 1, ActionPriority.CRITICAL, "revenue", 90.0),
        _make_daily_decision("dec-high", 2, ActionPriority.HIGH, "revenue", 90.0),
    ]
    audit = [
        {
            "decision_id": "dec-critical",
            "category": "revenue",
            "original_score": 90.0,
            "adjusted_score": 103.5,
            "multiplier": 1.15,
            "reason": "critical priority protected from reduction (category=revenue)",
        },
        {
            "decision_id": "dec-high",
            "category": "revenue",
            "original_score": 90.0,
            "adjusted_score": 76.5,
            "multiplier": 0.85,
            "reason": "negative preference bias",
        },
    ]

    async def _summary(*_a, **_kw):
        return _make_owner_summary("tenant-001", "empresa-001", decisions, audit)

    monkeypatch.setattr(mod._owner_intelligence_engine, "generate_action_center_summary", _summary)

    result = asyncio.run(
        mod.get_top5_decisions(tenant_id="tenant-001", empresa_codigo="empresa-001")
    )
    data = result["data"]
    critical_audit = next(a for a in data["preference_audit"] if a["decision_id"] == "dec-critical")
    assert critical_audit["multiplier"] >= 1.15
    assert "critical" in critical_audit["reason"].lower()
