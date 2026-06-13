"""Testes F07.8 — Commercial Learning & Recommendation Calibration."""
from __future__ import annotations

import pytest

from src.services.commercial_learning_service import CommercialLearningService, _confidence_level


def _sample_actions() -> list[dict]:
    return [
        {
            "id": "A1",
            "actionId": "A1",
            "tipo": "PROTEGER_MARGEM",
            "empresaCodigo": 11495,
            "lifecycleStatus": "VALIDADA",
            "hasExecutionEvidence": True,
            "responsavelNome": "JOÃO",
            "receitaPrevista": 100,
            "margemPrevista": 30,
            "receitaRealizada": 92,
            "margemRealizada": 28,
            "roiReal": 92,
            "roiRealCalculavel": True,
            "acuraciaReceitaPct": 92,
            "dataExecucao": "2026-06-04",
            "lineage": [{"origem": "F07.6", "snapshot": "action"}],
        },
        {
            "id": "A2",
            "actionId": "A2",
            "tipo": "REVISAR_PRECO",
            "empresaCodigo": 11495,
            "lifecycleStatus": "VALIDADA",
            "hasExecutionEvidence": True,
            "responsavelNome": "WANDERSON",
            "receitaPrevista": 50,
            "margemPrevista": 10,
            "receitaRealizada": 10,
            "margemRealizada": 2,
            "roiReal": 10,
            "roiRealCalculavel": True,
            "acuraciaReceitaPct": 20,
            "dataExecucao": "2026-06-05",
            "lineage": [{"origem": "F07.7", "snapshot": "execution"}],
        },
        {
            "id": "A3",
            "actionId": "A3",
            "tipo": "EXPANDIR_SORTIMENTO",
            "empresaCodigo": 5555,
            "lifecycleStatus": "RECOMENDADA",
            "hasExecutionEvidence": False,
            "responsavelNome": "JOÃO",
            "receitaPrevista": 20,
            "margemPrevista": 5,
            "receitaRealizada": 0,
            "margemRealizada": 0,
            "roiReal": 0,
            "roiRealCalculavel": False,
            "lineage": [{"origem": "F07.6", "snapshot": "action"}],
        },
    ]


def test_confidence_levels():
    assert _confidence_level(10) == "ALTA"
    assert _confidence_level(30) == "MEDIA"
    assert _confidence_level(80) == "BAIXA"


def test_recommendation_effectiveness():
    svc = CommercialLearningService()
    actions = svc._filter_actions(_sample_actions(), None)
    eff = svc._recommendation_effectiveness(actions)
    assert eff["totalTipos"] == 3
    proteger = next(t for t in eff["porTipo"] if t["tipo"] == "PROTEGER_MARGEM")
    assert proteger["validadas"] == 1
    assert proteger["roiReal"] == 92


def test_calibration_and_qa():
    svc = CommercialLearningService()
    actions = svc._filter_actions(_sample_actions(), None)
    calibration = svc._recommendation_calibration(actions)
    assert calibration["totalCalibradas"] == 2
    assert calibration["calibrations"][0]["confidenceLevel"] in ("ALTA", "MEDIA", "BAIXA")
    qa = svc._qa_gate(actions, None)
    assert qa["zeroAprendizadoSemEvidencia"] is True
    assert qa["zeroRecomendacaoInventada"] is True


@pytest.mark.asyncio
async def test_build_from_homologated_f077():
    svc = CommercialLearningService()
    resp = await svc.build("2026-06-01", "2026-06-07", None)
    if not resp.success:
        pytest.skip(f"Snapshot F07.7 indisponível: {resp.error}")
    data = resp.data
    assert data.get("sprint") == "F07.8"
    assert data.get("fonte", {}).get("webPostoLive") is False
    assert data.get("recommendationEffectivenessEngine")
    assert data.get("outcomeLearningEngine", {}).get("sistemaAprendendo") is True
