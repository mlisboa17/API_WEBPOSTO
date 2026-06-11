"""Testes F05.5 — Closed Loop Learning Engine."""
from __future__ import annotations

import pytest

from src.services.closed_loop_learning_engine_service import (
    ClosedLoopLearningEngineService,
    EFFECTIVENESS_LEVELS,
)


def test_effectiveness_levels_complete():
    assert len(EFFECTIVENESS_LEVELS) == 5
    assert "MUITO_EFETIVA" in EFFECTIVENESS_LEVELS
    assert "PREJUDICIAL" in EFFECTIVENESS_LEVELS


def test_roi_realizado_only_with_execution_evidence():
    svc = ClosedLoopLearningEngineService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    outcomes = [
        svc._outcome_measurement(rec, svc._resolve_action(rec, layers))
        for rec in layers["recommendations"]
    ]
    for outcome in outcomes:
        if outcome.get("roiRealizado") is not None:
            assert outcome.get("hasExecutionEvidence") is True


def test_learning_events_have_lineage_and_confidence():
    svc = ClosedLoopLearningEngineService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    outcomes = [
        svc._outcome_measurement(rec, svc._resolve_action(rec, layers))
        for rec in layers["recommendations"]
    ]
    rec_eval, _ = svc._recommendation_effectiveness_engine(outcomes, layers)
    action_eval = svc._action_effectiveness_engine(layers)
    events = svc._learning_engine(rec_eval, action_eval)
    assert events
    for event in events:
        assert event.get("lineage")
        assert event.get("confidenceLevel")
        assert event.get("learningScore") is not None


@pytest.mark.asyncio
async def test_build_full_payload():
    svc = ClosedLoopLearningEngineService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F05.5"
    assert data["fonte"]["webPosto"] is False
    assert data["fonte"]["execucaoAutomatica"] is False
    qa = data["qa"]
    assert qa["semCrossTenant"] is True
    assert qa["semRoiRealizadoSemExecutionEvidence"] is True
    assert qa["semScoreSemOrigem"] is True
    ex = data["executiveAnswers"]
    assert ex["1_recomendacoesAvaliadas"] > 0
    assert ex["19_sistemaAuditavel"] is True
    assert data["parecerFinal"].startswith("[PARECER FINAL:")
