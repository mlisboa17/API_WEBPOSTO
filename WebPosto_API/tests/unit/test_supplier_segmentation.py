"""Testes segmentação fornecedor — F01.4-D."""
from __future__ import annotations

from src.services.supplier_segmentation import (
    classify_supplier_segment,
    concentration_risk_level,
    is_strategic_homologated,
)


def test_vibra_homologated_no_concentration_alert() -> None:
    assert is_strategic_homologated("VIBRA")
    assert concentration_risk_level(89.99, "VIBRA") is None


def test_non_strategic_concentration_alert() -> None:
    assert concentration_risk_level(25.0, "O E C") == "HIGH"


def test_classify_priority_plano_conta() -> None:
    r = classify_supplier_segment(plano_categoria_v3="PESSOAL", supplier_name="VIBRA")
    assert r["supplierCategory"] == "RH"
    assert r["classificationSource"] == "PLANO_CONTA"


def test_classify_vibra_fornecedor() -> None:
    r = classify_supplier_segment(supplier_name="VIBRA ENERGIA S.A")
    assert r["supplierCategory"] == "ESTRATEGICOS"
    assert r["supplierStrategic"] is True


def test_classify_centro_pista() -> None:
    r = classify_supplier_segment(centro_custo="PISTA", supplier_name="GENERICO")
    assert r["supplierCategory"] == "ESTRATEGICOS"
    assert r["classificationSource"] == "CENTRO_CUSTO"
