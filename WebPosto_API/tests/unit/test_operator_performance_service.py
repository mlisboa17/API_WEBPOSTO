"""Testes unitários — Operator Performance F03.4."""
from __future__ import annotations

import pytest

from src.services.operator_performance_service import (
    PERFORMANCE_BANDS,
    W_COMPENSATED,
    W_DIFF,
    W_EVOLUTION,
    W_RECURRENCE,
    W_RISK,
    OperatorPerformanceService,
    _performance_band,
)


def test_performance_bands():
    assert _performance_band(95) == "Excelente"
    assert _performance_band(80) == "Bom"
    assert _performance_band(65) == "Atencao"
    assert _performance_band(40) == "Critico"
    assert len(PERFORMANCE_BANDS) == 4


def test_formula_weights_sum():
    total = W_DIFF + W_RECURRENCE + W_RISK + W_COMPENSATED + W_EVOLUTION
    assert round(total, 2) == 1.0


def test_score_operators_from_risk_fallback():
    svc = OperatorPerformanceService()
    cash_payload = {
        "operators": {"todos": []},
        "riskScore": {
            "operadores": [
                {
                    "funcionarioCodigo": 276288,
                    "diferencaAcumulada": -500.0,
                    "indiceRecorrencia": 0.8,
                    "cashRiskScore": 35,
                },
                {
                    "funcionarioCodigo": 294273,
                    "diferencaAcumulada": -200.0,
                    "indiceRecorrencia": 0.3,
                    "cashRiskScore": 70,
                },
            ]
        },
    }
    ledger = {
        276288: {"faltas": 1000, "compensadoAutomatico": 100, "saldo": -900},
        294273: {"faltas": 200, "compensadoAutomatico": 150, "saldo": -50},
    }
    scored = svc._score_operators(cash_payload, ledger)
    assert len(scored) == 2
    assert scored[0]["performanceScore"] >= scored[1]["performanceScore"]
    assert all("performanceBand" in o for o in scored)
    assert scored[-1]["funcionarioCodigo"] == 276288


def test_score_pdvs_critical_flag():
    svc = OperatorPerformanceService()
    cash_payload = {
        "pdvs": {
            "ranking": [
                {"pdvCodigo": 54193, "diferencaAcumulada": -800, "fechamentos": 10, "cashRiskScore": 30},
                {"pdvCodigo": 15880, "diferencaAcumulada": -400, "fechamentos": 8, "cashRiskScore": 45},
            ]
        }
    }
    pdvs = svc._score_pdvs(cash_payload)
    crit = {p["pdvCodigo"]: p for p in pdvs if p.get("monitoramentoPrioritario")}
    assert 54193 in crit
    assert 15880 in crit


def test_evolution_report():
    windows = {
        "7d": {
            "operators": [
                {"funcionarioCodigo": 1, "performanceScore": 50, "performanceBand": "Critico"},
                {"funcionarioCodigo": 2, "performanceScore": 80, "performanceBand": "Bom"},
            ]
        },
        "30d": {
            "operators": [
                {"funcionarioCodigo": 1, "performanceScore": 55},
                {"funcionarioCodigo": 2, "performanceScore": 78},
            ]
        },
        "90d": {
            "operators": [
                {"funcionarioCodigo": 1, "performanceScore": 65, "performanceBand": "Atencao"},
                {"funcionarioCodigo": 2, "performanceScore": 70, "performanceBand": "Atencao"},
            ]
        },
    }
    evo = OperatorPerformanceService._evolution_report(windows)
    assert "melhorando" in evo
    assert "piorando" in evo
    improving = {x["funcionarioCodigo"] for x in evo["melhorando"]}
    assert 1 in improving
