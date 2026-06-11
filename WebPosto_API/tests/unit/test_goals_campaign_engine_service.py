"""Testes F04.5 — Goals & Campaign Engine."""
from __future__ import annotations

from src.services.goals_campaign_engine_service import GoalsCampaignEngineService, _pct


def test_pct_higher_is_better():
    assert _pct(105, 100, True) == 105.0


def test_goal_model_count():
    svc = GoalsCampaignEngineService()
    operators = [
        {
            "funcionarioCodigo": 1,
            "employeeName": "A",
            "receitaBruta": 1000,
            "ticketMedio": 50,
            "globalScore": 80,
            "accountabilityScore": 90,
            "destruicaoMargem": 100,
        }
    ]
    goals = svc._goal_model_engine(operators)
    assert len(goals) == 5


def test_achievement_status():
    svc = GoalsCampaignEngineService()
    goals = [
        {
            "goalId": "1:VENDA",
            "funcionarioCodigo": 1,
            "employeeName": "A",
            "goalType": "VENDA",
            "scope": "OPERADOR",
            "targetValue": 100.0,
            "unit": "BRL",
            "higherIsBetter": True,
        }
    ]
    operators = [{"funcionarioCodigo": 1, "employeeName": "A", "receitaBruta": 110}]
    ach = svc._goal_achievement_engine(goals, operators)
    assert ach[0]["status"] in ("ATINGIU", "SUPEROU")


def test_bonus_blocks_on_audit():
    svc = GoalsCampaignEngineService()
    operators = [{"funcionarioCodigo": 1, "employeeName": "X", "recommendedActions": ["AUDITAR"], "riskScore": 80, "resultadoLiquido": 1000}]
    achievements = [{"funcionarioCodigo": 1, "percentualAtingido": 90, "goalType": "VENDA", "goalId": "1:VENDA"}]
    bonuses = svc._bonus_simulation_engine(operators, achievements, {"bonusEngineV2": {"candidates": []}})
    assert bonuses[0]["riscoBloqueante"] is True
    assert bonuses[0]["bonusSugerido"] == 0.0


def test_qa_paridade_zero():
    svc = GoalsCampaignEngineService()
    qa = svc._qa_engine(
        [{"percentualAtingido": 90, "goalId": "1:VENDA", "funcionarioCodigo": 1}],
        [{"elegivel": True, "evidence": {"x": 1}}],
        {"executiveAnswers": {"paridadeDelta": 0}},
        {"executiveAnswers": {"paridadeDelta": 0}},
        {"executiveAnswers": {"paridadeDelta": 0}},
    )
    assert qa["paridadeZero"] is True
