"""Testes F04.1 — Operator Accountability & Incentive Engine."""
from __future__ import annotations

from src.services.operator_accountability_incentive_service import (
    OperatorAccountabilityIncentiveService,
    _global_band,
    _norm_score,
)


def test_global_band_elite():
    assert _global_band(95) == "ELITE"


def test_global_band_critico():
    assert _global_band(10) == "CRÍTICO"


def test_norm_score():
    assert _norm_score(50, 100) == 50.0


def test_sales_score_engine():
    svc = OperatorAccountabilityIncentiveService()
    sales = [
        {
            "funcionarioCodigo": 1,
            "employeeName": "A",
            "quantidadeVendas": 10,
            "totalVendas": 1000,
            "ticketMedio": 100,
            "volumeCombustivel": 800,
            "volumeConveniencia": 200,
        },
        {
            "funcionarioCodigo": 2,
            "employeeName": "B",
            "quantidadeVendas": 5,
            "totalVendas": 500,
            "ticketMedio": 100,
            "volumeCombustivel": 400,
            "volumeConveniencia": 100,
        },
    ]
    scored = svc._sales_score_engine(sales)
    assert scored[0]["funcionarioCodigo"] == 1
    assert scored[0]["salesScore"] >= scored[1]["salesScore"]


def test_accountability_score_sobras_bonus():
    svc = OperatorAccountabilityIncentiveService()
    accountability = [
        {
            "funcionarioCodigo": 1,
            "employeeName": "Credor",
            "faltasProxy": 0,
            "sobrasProxy": 100,
            "compensadoAutomatico": 50,
            "saldoOperacional": 100,
        },
        {
            "funcionarioCodigo": 2,
            "employeeName": "Devedor",
            "faltasProxy": -100,
            "sobrasProxy": 0,
            "compensadoAutomatico": 0,
            "saldoOperacional": -100,
        },
    ]
    perf = [
        {"funcionarioCodigo": 1, "diferencaAcumulada": 0},
        {"funcionarioCodigo": 2, "diferencaAcumulada": -100},
    ]
    scored = svc._accountability_score_engine(accountability, perf)
    credor = next(r for r in scored if r["funcionarioCodigo"] == 1)
    devedor = next(r for r in scored if r["funcionarioCodigo"] == 2)
    assert credor["accountabilityScore"] > devedor["accountabilityScore"]


def test_bonus_eligibility():
    svc = OperatorAccountabilityIncentiveService()
    operators = [
        {
            "funcionarioCodigo": 1,
            "globalScore": 90,
            "accountabilityScore": 80,
            "complianceScore": 85,
            "globalClassification": "ELITE",
        },
        {
            "funcionarioCodigo": 2,
            "globalScore": 30,
            "accountabilityScore": 20,
            "complianceScore": 25,
            "globalClassification": "CRÍTICO",
        },
    ]
    out = svc._bonus_eligibility_engine(operators)
    assert out[0]["bonusEligibility"] == "Elegível"
    assert out[1]["bonusEligibility"] == "Não Elegível"
