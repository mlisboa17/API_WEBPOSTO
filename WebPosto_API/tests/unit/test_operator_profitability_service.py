"""Testes F04.2 — Operator Profitability Engine."""
from __future__ import annotations

from src.services.operator_profitability_service import (
    OperatorProfitabilityService,
    _profitability_band,
)


def test_profitability_band_lucro():
    assert _profitability_band(85) == "GERA_LUCRO"


def test_profitability_band_destrui():
    assert _profitability_band(20) == "DESTRUI_MARGEM"


def test_revenue_engine():
    svc = OperatorProfitabilityService()
    sales = [
        {
            "funcionarioCodigo": 1,
            "employeeName": "A",
            "totalVendas": 1000,
            "volumeCombustivel": 800,
            "volumeConveniencia": 200,
            "ticketMedio": 100,
            "volumeFinanceiro": 1000,
            "quantidadeVendas": 10,
        }
    ]
    rev = svc._revenue_engine(sales)
    assert rev[0]["receitaBruta"] == 1000.0


def test_margin_impact():
    svc = OperatorProfitabilityService()
    revenue = [{"funcionarioCodigo": 1, "employeeName": "A", "receitaBruta": 1000.0}]
    discounts = {"descontoPorOperador": [{"funcionarioCodigo": 1, "totalDesconto": 50}]}
    accountability = [{"funcionarioCodigo": 1, "faltasProxy": -20, "sobrasProxy": 0, "saldoOperacional": -20}]
    perf = [{"funcionarioCodigo": 1, "diferencaAcumulada": -10}]
    margin = svc._margin_impact_engine(revenue, discounts, accountability, perf, [])
    assert margin[0]["destruicaoMargem"] > 0
    assert margin[0]["margemOperacional"] < 1000


def test_management_actions_auditar():
    svc = OperatorProfitabilityService()
    profitability = [
        {
            "funcionarioCodigo": 9,
            "employeeName": "Critico",
            "profitabilityScore": 25,
            "profitabilityBand": "DESTRUI_MARGEM",
            "resultadoLiquido": -50,
        }
    ]
    roi = [{"funcionarioCodigo": 9, "roi": 0.5}]
    people = [{"funcionarioCodigo": 9, "globalClassification": "CRÍTICO", "accountabilityScore": 30, "complianceScore": 30}]
    actions = svc._management_action_engine(profitability, roi, people, [])
    assert "AUDITAR" in actions[0]["managementActions"]
