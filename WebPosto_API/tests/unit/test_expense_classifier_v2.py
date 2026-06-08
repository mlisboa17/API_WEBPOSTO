"""Testes classificador V2 — F01.3."""
from __future__ import annotations

from src.services.logos_expense_classifier import classify_logos_expense, classify_logos_expense_full
from src.services.logos_expense_classifier_v2 import classify_logos_expense_v2, map_v2_to_legacy


def test_v2_energia_solar() -> None:
    r = classify_logos_expense_v2("REF NF:000064790 - SOLAR INOVE - PERNAMBUCO")
    assert r.categoria_v2 == "ENERGIA"
    assert r.confidence_score >= 80


def test_v2_pessoal_quinzena() -> None:
    r = classify_logos_expense_v2("QUINZENA CRISTIANE")
    assert r.categoria_v2 == "PESSOAL"
    assert r.confidence_score >= 80


def test_legacy_retrocompat() -> None:
    assert classify_logos_expense("Vale de funcionário", "") == "PESSOAL"
    full = classify_logos_expense_full("Vale de funcionário", "")
    assert full["categoriaLogos"] == "PESSOAL"
    assert full["categoriaLogosV2"] == "PESSOAL"
    assert full["confidenceScore"] >= 60


def test_v2_low_confidence_outros() -> None:
    r = classify_logos_expense_v2("pagamento alamoa")
    assert r.categoria_v2 == "OUTROS" or r.confidence_score < 60


def test_legacy_mapping() -> None:
    assert map_v2_to_legacy("ENERGIA") == "OPERACIONAL"
    assert map_v2_to_legacy("MARKETING") == "COMERCIAL"
