"""Testes MDM fornecedor — F01.4-C."""
from __future__ import annotations

from src.services.supplier_mdm import (
    canonical_supplier_name,
    compute_supplier_coverage_score,
    extract_supplier_from_expense_description,
    normalize_supplier_key,
)


def test_canonical_ipiranga() -> None:
    assert canonical_supplier_name("IPIRANGA S.A.") == "IPIRANGA"
    assert canonical_supplier_name("IPIRANGA DISTRIBUIDORA") == "IPIRANGA"


def test_canonical_ambev() -> None:
    assert canonical_supplier_name("AMBEV S.A.") == "AMBEV"
    assert canonical_supplier_name("CIA DE BEBIDAS AMBEV") == "AMBEV"


def test_normalize_key() -> None:
    assert normalize_supplier_key("Vibra Energia S.A.") == "VIBRA ENERGIA S A"
    assert canonical_supplier_name("Vibra Energia S.A.") == "VIBRA"


def test_extract_ref_nf() -> None:
    desc = "REF NF:000064790 - SOLAR INOVE - PERNAMBUCO - SOLAR INOVE"
    assert extract_supplier_from_expense_description(desc) == "SOLAR INOVE"


def test_coverage_score_full() -> None:
    score = compute_supplier_coverage_score(
        {
            "supplierName": "VIBRA",
            "supplierDocument": "12345678000199",
            "supplierCode": 42,
            "empresaCodigo": "11495",
        }
    )
    assert score == 100
