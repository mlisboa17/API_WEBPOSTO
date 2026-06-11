"""Testes F04.4 — Management Action Center."""
from __future__ import annotations

from src.services.management_action_center_service import (
    ManagementActionCenterService,
    _risk_score,
    _roi_norm,
)


def test_roi_norm_pct():
    assert _roi_norm({"roiPct": 85.5}) == 85.5


def test_risk_score_high_destruction():
    row = {
        "accountabilityScore": 30,
        "complianceScore": 100,
        "destruicaoMargem": 500,
        "receitaBruta": 1000,
        "profitabilityBand": "NEUTRO",
        "globalClassification": "CRÍTICO",
    }
    assert _risk_score(row) >= 70


def test_action_engine_promover():
    svc = ManagementActionCenterService()
    operators = [
        {
            "funcionarioCodigo": 1,
            "employeeName": "Elite",
            "globalScore": 90,
            "accountabilityScore": 95,
            "roiPct": 100,
            "resultadoLiquido": 1000,
            "globalClassification": "ELITE",
            "profitabilityBand": "GERA_LUCRO",
            "bonusEligibility": "Elegível",
            "faltas": 0,
            "destruicaoMargem": 0,
            "receitaBruta": 1000,
        }
    ]
    operators[0]["riskScore"] = _risk_score(operators[0])
    actions = svc._action_engine(operators, {"contextFairnessEngine": {}}, {"criticalPdvForensics": {}})
    assert "PROMOVER" in actions[0]["recommendedActions"]
    assert actions[0]["evidence"]["PROMOVER"]["globalScore"] >= 85


def test_governance_embaixador():
    svc = ManagementActionCenterService()
    operators = [
        {
            "funcionarioCodigo": 1,
            "employeeName": "A",
            "globalScore": 92,
            "accountabilityScore": 95,
            "profitabilityBand": "GERA_LUCRO",
        }
    ]
    actions = [{"funcionarioCodigo": 1, "recommendedActions": ["PROMOVER"], "primaryAction": "PROMOVER"}]
    gov = svc._governance_engine(operators, actions)
    assert gov[0]["governanceBand"] == "EMBAIXADOR"


def test_qa_evidence_complete():
    svc = ManagementActionCenterService()
    actions = [
        {
            "funcionarioCodigo": 1,
            "primaryAction": "PROMOVER",
            "evidence": {
                "PROMOVER": {
                    "globalScore": 90,
                    "accountabilityScore": 95,
                    "roiNorm": 100,
                    "critical": False,
                }
            },
        }
    ]
    qa = svc._qa_engine(actions, {"executiveAnswers": {"paridadeDelta": 0}}, {"executiveAnswers": {"paridadeDelta": 0}})
    assert qa["evidenciaCompleta"] is True
    assert qa["paridadeZero"] is True
