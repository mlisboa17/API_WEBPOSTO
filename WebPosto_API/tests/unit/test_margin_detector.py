"""Unit tests — MarginDetector (Sprint 2)."""

from __future__ import annotations

from src.services.decision_discovery.detectors.margin_detector import MarginDetector


def test_margin_deviation_detected():
    detector = MarginDetector()
    payload = {
        "tenant_id": "74014",
        "margin_target_pct": 0.12,
        "data_quality": 0.9,
        "fuel_rows": [
            {"combustivel": "Diesel S10", "litros": 10000, "valor": 62000},
        ],
        "purchase_rows": [
            {
                "empresaCodigo": "74014",
                "descricaoProduto": "Diesel S10",
                "quantidade": 10000,
                "valorTotal": 58000,
            }
        ],
    }
    analyses = detector._analyze_margin_deviations(payload)
    assert analyses
    top = analyses[0]
    assert top["product_name"] == "Diesel S10"
    assert top["margin_gap_pct"] > 0
    assert top["impact_brl"] > 0


def test_margin_ok_when_above_target():
    detector = MarginDetector()
    payload = {
        "tenant_id": "74014",
        "margin_target_pct": 0.05,
        "data_quality": 0.9,
        "fuel_rows": [
            {"combustivel": "Gasolina", "litros": 5000, "valor": 35000},
        ],
        "purchase_rows": [
            {
                "empresaCodigo": "74014",
                "descricaoProduto": "Gasolina",
                "quantidade": 5000,
                "valorTotal": 30000,
            }
        ],
    }
    analyses = detector._analyze_margin_deviations(payload)
    assert analyses == []
