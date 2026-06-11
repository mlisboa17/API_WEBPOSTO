"""Testes F04.3 — Store & Shift Profitability Engine."""
from __future__ import annotations

from src.services.store_shift_profitability_service import (
    StoreShiftProfitabilityService,
    _operation_band,
    _turn_key,
)


def test_operation_band_excelente():
    assert _operation_band(85) == "EXCELENTE"


def test_operation_band_critico():
    assert _operation_band(25) == "CRÍTICO"


def test_turn_key_label():
    assert _turn_key({"turnoCodigo": 1}) == "1º Turno"


def test_aggregate_sales_parity():
    svc = StoreShiftProfitabilityService()
    venda = [
        {"funcionarioCodigo": 1, "pdvCodigo": 100, "turnoCodigo": 1, "totalVenda": 500, "cancelado": "N"},
        {"funcionarioCodigo": 2, "pdvCodigo": 200, "turnoCodigo": 2, "totalVenda": 300, "cancelado": "N"},
    ]
    by_pdv, by_turn, by_cell, consolidated = svc._aggregate_sales(venda)
    assert consolidated == 800.0
    assert by_pdv[100]["receitaBruta"] == 500.0
    assert by_turn["1º Turno"]["receitaBruta"] == 500.0
    assert len(by_cell) == 2


def test_pdv_profitability_engine():
    svc = StoreShiftProfitabilityService()
    by_pdv = {100: {"receitaBruta": 1000.0, "quantidadeVendas": 5, "cancelamentos": 0.0}}
    discounts = {"descontoPorPdv": [{"pdvCodigo": 100, "totalDesconto": 50}]}
    cash_pdvs = [{"pdvCodigo": 100, "diferencaAcumulada": -20}]
    rows = svc._pdv_profitability_engine(by_pdv, discounts, cash_pdvs)
    assert rows[0]["receitaBruta"] == 1000.0
    assert rows[0]["margemOperacional"] < 1000.0


def test_enrich_venda_from_cash():
    svc = StoreShiftProfitabilityService()
    venda = [{"funcionarioCodigo": 1, "totalVenda": 100, "cancelada": "N"}]
    merged = [{"funcionarioCodigo": 1, "pdvCodigo": 54193, "turnoCodigo": 1, "diferenca": 0}]
    out = svc._enrich_venda_from_cash(venda, merged)
    assert out[0]["pdvCodigo"] == 54193
    assert out[0]["turno"] == "1º Turno"


def test_operational_roi_engine():
    svc = StoreShiftProfitabilityService()
    matrix = [
        {
            "pdvCodigo": 1,
            "turno": "1º Turno",
            "receitaBruta": 100,
            "resultadoLiquido": 80,
            "riscoEconomico": 20,
        },
        {
            "pdvCodigo": 1,
            "turno": "2º Turno",
            "receitaBruta": 50,
            "resultadoLiquido": 10,
            "riscoEconomico": 40,
        },
    ]
    roi = svc._operational_roi_engine(matrix)
    assert roi["maiorRoi"]["turno"] == "1º Turno"
    assert roi["menorRoi"]["turno"] == "2º Turno"
