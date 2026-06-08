"""Testes classificador V3 — F01.4-A."""
from __future__ import annotations

from src.services.logos_expense_classifier_v3 import classify_logos_expense_v3, classify_with_all_versions


def test_v3_plano_conta_salarios() -> None:
    r = classify_logos_expense_v3(
        descricao="pagamento aleatorio",
        plano_conta_gerencial_codigo=29072,
    )
    assert r.categoria_v3 == "PESSOAL"
    assert r.classification_source in ("PLANO_CONTA", "MANUAL", "HIBRIDO")
    assert 0.0 <= r.confidence_score <= 1.0


def test_v3_confidence_never_above_one() -> None:
    full = classify_with_all_versions(
        descricao="QUINZENA CRISTIANE",
        plano_conta_gerencial_codigo=29072,
    )
    assert full["confidenceScoreV3"] <= 1.0
    assert full["classificationSource"] in {
        "PLANO_CONTA", "CENTRO_CUSTO", "FORNECEDOR", "DESCRICAO", "HIBRIDO", "MANUAL", "OUTROS"
    }


def test_v3_retrocompat_fields() -> None:
    full = classify_with_all_versions(descricao="Vale de funcionário", plano_conta_gerencial_codigo=29072)
    assert full["categoriaLogos"]
    assert full["categoriaLogosV2"]
    assert full["categoriaLogosV3"]
    assert isinstance(full["confidenceScore"], int)


def test_v3_fallback_descricao() -> None:
    r = classify_logos_expense_v3(descricao="FRETE TELHA")
    assert r.categoria_v3 == "FRETES"
    assert r.classification_source == "DESCRICAO"
