"""Testes F05.4 — Autonomous Recommendation Engine."""
from __future__ import annotations

import pytest

from src.services.autonomous_recommendation_engine_service import (
    AutonomousRecommendationEngineService,
    LIFECYCLE_STATES,
)


def test_lifecycle_states_complete():
    assert len(LIFECYCLE_STATES) == 6
    assert "GERADA" in LIFECYCLE_STATES
    assert "CONVERTIDA_EM_ACAO" in LIFECYCLE_STATES


def test_no_automatic_execution():
    svc = AutonomousRecommendationEngineService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    opps = svc._opportunity_discovery_engine(layers)
    risks = svc._risk_discovery_engine(layers)
    for item in opps + risks:
        assert item.get("execucaoAutomatica") is False
        assert item.get("lineage")
        assert item.get("confidenceLevel")
        assert item.get("evidenceSource") is not None


def test_roi_forecast_never_realized_without_evidence():
    svc = AutonomousRecommendationEngineService()
    rec = {
        "_roi_base": 1000,
        "impacto": 500,
        "confidenceLevel": "ALTA",
    }
    forecast = svc._roi_forecast(rec, None)
    assert forecast["roiLabel"] == "ROI_PREVISTO"
    assert forecast["roiRealizado"] is None


def test_prioritization_assigns_p1_p2_p3():
    svc = AutonomousRecommendationEngineService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    combined = svc._opportunity_discovery_engine(layers) + svc._risk_discovery_engine(layers)
    ranked = svc._prioritization_engine(combined, layers)
    assert ranked
    for row in ranked:
        assert row.get("priority") in ("P1", "P2", "P3")
        assert row.get("impactScore") is not None
        assert row.get("roiScore") is not None
        assert row.get("urgencyScore") is not None
        assert row.get("roiMedio") is not None


@pytest.mark.asyncio
async def test_build_full_payload():
    svc = AutonomousRecommendationEngineService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F05.4"
    assert data["fonte"]["webPosto"] is False
    assert data["fonte"]["execucaoAutomatica"] is False
    qa = data["qa"]
    assert qa["semCrossTenant"] is True
    assert qa["semExecucaoAutomatica"] is True
    assert qa["semRecomendacaoSemLineage"] is True
    assert qa["semRecomendacaoSemRoi"] is True
    ex = data["executiveAnswers"]
    assert ex["1_totalRecomendacoes"] > 0
    assert ex["15_semJustificativa"] == 0
    assert ex["17_execucaoAutomatica"] is False
    assert data["parecerFinal"].startswith("[PARECER FINAL:")
