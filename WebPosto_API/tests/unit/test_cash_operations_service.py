"""Testes unitários — Cash Operations F03."""
from __future__ import annotations

import pytest

from src.services.cash_operations_service import (
    ALERT_ATENCAO,
    ALERT_CRITICO,
    W_HIST,
    W_OPERATOR,
    W_PDV,
    W_TURN,
    CashOperationsService,
    _alert_level,
    _risk_band,
    safe_float,
    safe_int,
)


def _sample_rows() -> list[dict]:
    return [
        {
            "caixaCodigo": 1,
            "empresaCodigo": 5555,
            "funcionarioCodigo": 276288,
            "pdvCodigo": 54193,
            "turnoCodigo": 1,
            "turno": "1º TURNO",
            "dataMovimento": "2026-06-01",
            "apurado": 10000,
            "diferenca": -120.0,
        },
        {
            "caixaCodigo": 2,
            "empresaCodigo": 5555,
            "funcionarioCodigo": 276288,
            "pdvCodigo": 54193,
            "turnoCodigo": 1,
            "turno": "1º TURNO",
            "dataMovimento": "2026-06-02",
            "apurado": 9000,
            "diferenca": -15.0,
        },
        {
            "caixaCodigo": 3,
            "empresaCodigo": 5555,
            "funcionarioCodigo": 294273,
            "pdvCodigo": 15880,
            "turnoCodigo": 1,
            "turno": "1º TURNO",
            "dataMovimento": "2026-06-03",
            "apurado": 8000,
            "diferenca": -252.27,
        },
        {
            "caixaCodigo": 4,
            "empresaCodigo": 5555,
            "funcionarioCodigo": 294273,
            "pdvCodigo": 15880,
            "turnoCodigo": 2,
            "turno": "2º TURNO",
            "dataMovimento": "2026-06-04",
            "apurado": 7000,
            "diferenca": 0.0,
        },
    ]


def test_alert_levels():
    assert _alert_level(0.0, 0, 0) == "OK"
    assert _alert_level(5.0, 0, 0) == "INFO"
    assert _alert_level(ALERT_ATENCAO, 0, 0) == "ATENCAO"
    assert _alert_level(50.0, 0, 0) == "ALTO"
    assert _alert_level(ALERT_CRITICO, 0, 0) == "CRITICO"
    assert _alert_level(10.0, 3, 0) == "CRITICO"
    assert _alert_level(10.0, 0, 5) == "CRITICO"


def test_risk_bands():
    assert _risk_band(95) == "Excelente"
    assert _risk_band(80) == "Bom"
    assert _risk_band(65) == "Atencao"
    assert _risk_band(40) == "Critico"


def test_risk_weights_sum():
    assert round(W_OPERATOR + W_PDV + W_TURN + W_HIST, 2) == 1.0


def test_alert_engine_counts():
    svc = CashOperationsService()
    rows = _sample_rows()
    consecutive = svc._consecutive_breaks(rows)
    pdv_30d = svc._pdv_breaks_30d(rows)
    alerts = svc._build_alerts(rows, consecutive, pdv_30d)
    assert alerts["total"] >= 3
    assert alerts["porNivel"]["CRITICO"] >= 1


def test_risk_score_structure():
    svc = CashOperationsService()
    rows = _sample_rows()
    risk = svc._build_risk_score(rows, rows)
    assert "consolidado" in risk
    assert risk["pesos"]["operador"] == W_OPERATOR
    assert risk["band"] in {"Excelente", "Bom", "Atencao", "Critico"}


def test_operator_analytics_rankings():
    svc = CashOperationsService()
    rows = _sample_rows()
    risk = svc._build_risk_score(rows, rows)
    ops = svc._operator_analytics(rows, risk)
    assert len(ops["rankingPiores"]) <= 20
    assert len(ops["rankingMelhores"]) <= 20
    assert ops["totalOperadores"] == 2


def test_pdv_critical_focus():
    svc = CashOperationsService()
    rows = _sample_rows()
    risk = svc._build_risk_score(rows, rows)
    pdvs = svc._pdv_analytics(rows, risk)
    assert pdvs["alvosCriticos"]["54193"] is not None
    assert pdvs["alvosCriticos"]["15880"] is not None


def test_snapshot_ttl_constant():
    from src.services.cash_operations_snapshot_service import CASH_OPERATIONS_SNAPSHOT_TTL_SECONDS

    assert CASH_OPERATIONS_SNAPSHOT_TTL_SECONDS == 300.0


def test_safe_float_handles_nullable_values():
    assert safe_float(None) == 0.0
    assert safe_float("") == 0.0
    assert safe_float("12.5") == 12.5
    assert safe_float("invalid", 3.0) == 3.0


def test_operator_with_null_risk_score():
    svc = CashOperationsService()
    rows = _sample_rows()
    risk = svc._build_risk_score(rows, rows)
    for op in risk["operadores"]:
        op["score"] = None
    ops = svc._operator_analytics(rows, risk)
    assert ops["totalOperadores"] == 2
    assert len(ops["rankingMelhores"]) <= 20


def test_operator_with_missing_risk_score():
    svc = CashOperationsService()
    rows = _sample_rows()
    ops = svc._operator_analytics(rows, {"operadores": [], "pdvs": []})
    assert all(item.get("cashRiskScore") is None for item in ops["todos"])
    assert ops["rankingPiores"]


def test_operator_with_empty_risk_score():
    svc = CashOperationsService()
    rows = _sample_rows()
    risk = {"operadores": [{"funcionarioCodigo": 276288, "score": "", "band": "Critico"}], "pdvs": []}
    ops = svc._operator_analytics(rows, risk)
    assert ops["rankingMelhores"] is not None


def test_operator_with_null_fechamentos():
    items = [
        {"cashRiskScore": 50.0, "fechamentos": None, "diferencaAcumulada": 10.0},
        {"cashRiskScore": None, "fechamentos": 3, "diferencaAcumulada": 5.0},
    ]
    ranked = sorted(
        items,
        key=lambda x: (-safe_float(x.get("cashRiskScore")), -safe_int(x.get("fechamentos"))),
    )
    assert len(ranked) == 2


def test_operator_sorting_with_partial_data():
    svc = CashOperationsService()
    rows = _sample_rows()
    risk = svc._build_risk_score(rows, rows)
    risk["operadores"] = [
        {"funcionarioCodigo": 276288, "score": None, "band": "Critico"},
        {"funcionarioCodigo": 294273, "score": 80.0, "band": "Bom"},
    ]
    ops = svc._operator_analytics(rows, risk)
    best_scores = [item.get("cashRiskScore") for item in ops["rankingMelhores"]]
    assert 80.0 in best_scores or None in best_scores
    assert safe_int(None) == 0
