"""Testes F05.1 — Executive Decision Engine."""
from __future__ import annotations

import pytest

from src.services.executive_decision_engine_service import (
    D05_AUDIT,
    ExecutiveDecisionEngineService,
    F050_AUDIT,
    MANDATORY_PDVS,
    MANDATORY_PEOPLE,
    RISK_STRATEGIES,
)


def test_audits_exist():
    assert D05_AUDIT.exists()
    assert F050_AUDIT.exists()


def test_trust_executivo_above_threshold():
    svc = ExecutiveDecisionEngineService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    trust = svc._trust_executivo(layers)
    assert trust >= 70


def test_opportunity_decision_engine():
    svc = ExecutiveDecisionEngineService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    trust = svc._trust_executivo(layers)
    actions = svc._opportunity_decision_engine(layers, trust)
    assert actions
    assert all(a.get("calculoRoi") for a in actions)
    assert all(a.get("lineage") for a in actions)


def test_risk_decision_engine_strategies():
    svc = ExecutiveDecisionEngineService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    trust = svc._trust_executivo(layers)
    actions = svc._risk_decision_engine(layers, trust)
    assert actions
    for action in actions:
        assert action.get("classificacaoRisco") in RISK_STRATEGIES


def test_financial_action_engine():
    svc = ExecutiveDecisionEngineService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    trust = svc._trust_executivo(layers)
    actions = svc._financial_action_engine(layers, trust)
    assert actions
    temas = {a.get("tema") for a in actions}
    assert "PERDAS" in temas
    assert "CAIXA" in temas


def test_mandatory_people_cases():
    svc = ExecutiveDecisionEngineService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    trust = svc._trust_executivo(layers)
    actions = svc._people_action_engine(layers, trust)
    names = " ".join(str(a.get("employeeName") or a.get("acao") or "") for a in actions).upper()
    codes = {str(a.get("funcionarioCodigo")) for a in actions}
    for token in MANDATORY_PEOPLE:
        if token.isdigit():
            assert token in codes or any(token in str(a.get("acao", "")) for a in actions)
        else:
            assert token in names or any(token in str(a.get("acao", "")).upper() for a in actions)


def test_mandatory_operations_cases():
    svc = ExecutiveDecisionEngineService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    trust = svc._trust_executivo(layers)
    actions = svc._operations_action_engine(layers, trust)
    pdvs = {a.get("pdvCodigo") for a in actions}
    for pdv in MANDATORY_PDVS:
        assert pdv in pdvs
    assert any(a.get("turno") == "1º Turno" for a in actions)
    assert any(a.get("empresaCodigo") == 5333 for a in actions)


def test_roi_prioritization():
    svc = ExecutiveDecisionEngineService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    trust = svc._trust_executivo(layers)
    all_actions = (
        svc._opportunity_decision_engine(layers, trust)
        + svc._risk_decision_engine(layers, trust)
        + svc._financial_action_engine(layers, trust)
        + svc._people_action_engine(layers, trust)
        + svc._operations_action_engine(layers, trust)
    )
    prioritized = svc._roi_prioritization_engine(all_actions)
    assert prioritized["prioridade1"]
    assert prioritized["total"] == len(all_actions)
    p1 = prioritized["prioridade1"]
    p2 = prioritized["prioridade2"]
    assert all(a.get("prioridade") == 1 for a in p1)
    assert all(a.get("prioridade") == 2 for a in p2)


@pytest.mark.asyncio
async def test_build_full_payload():
    svc = ExecutiveDecisionEngineService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F05.1"
    assert data["fonte"]["webPosto"] is False
    assert data["cockpit"]["topDecisoes"]
    assert data["executiveAnswers"]["14_planoCorporativoConsolidado"]
    assert data["qa"]["trustExecutivoOk"] is True
    assert data["executiveAnswers"]["18_motorAuditavel"] is True
