"""Testes F07.6 — Commercial Action Center."""
from __future__ import annotations

from src.services.commercial_action_center_service import CommercialActionCenterService


def test_build_commercial_actions():
    svc = CommercialActionCenterService()
    assortment = {
        "commercialFocus": {
            "produtosFoco": [
                {
                    "produtoCodigo": 100,
                    "receita": 50,
                    "margemPct": 40,
                    "focoComercialScore": 80,
                    "acoesRecomendadas": ["PROTEGER_MARGEM"],
                    "filiaisAtivas": [11495],
                }
            ]
        },
        "highVolumeLowMargin": {"produtos": []},
        "expansionPotential": {"produtos": []},
        "branchBenchmarkGap": {"filiaisAbaixoBenchmark": []},
        "fuelDependencyRisk": {"filiaisRisco": []},
    }
    actions = svc._build_commercial_actions(assortment, {"receitaProdutosVendidos": 1104}, {}, {})
    assert actions
    assert actions[0]["responsavel"]["ownerName"]
    assert actions[0]["evidencia"]
    assert actions[0]["status"] in ("RECOMENDADA", "APROVADA", "EM_ANDAMENTO")


def test_action_center_summary():
    svc = CommercialActionCenterService()
    actions = [
        {
            "prioridade": "ALTA",
            "status": "APROVADA",
            "impactoEstimadoReceita": 100,
            "impactoEstimadoMargem": 30,
            "responsavel": {"ownerName": "Test"},
            "evidencia": {"x": 1},
            "lineage": [{}],
        }
    ]
    summary = svc._action_center_summary(actions)
    assert summary["totalAcoes"] == 1
    assert summary["impactoTotalReceita"] == 100
