"""Conversao de embalagem para unidade de venda usando a quantidade tributavel da nota."""

from __future__ import annotations

from decimal import Decimal

from src.operational.product_registration.dfe_cost_resolver import (
    QUANTITY_FROM_COMMERCIAL,
    QUANTITY_FROM_TAXABLE,
    InvoiceTotals,
    compute_unit_cost,
    resolve_sale_unit_quantity,
)


def _totals(produtos: str) -> InvoiceTotals:
    return InvoiceTotals(produtos=Decimal(produtos))


def test_commercial_unit_that_is_the_sale_unit_answers_directly():
    item = {"u_com": "UN", "q_com": "12", "u_trib": "UN", "q_trib": "12"}

    assert resolve_sale_unit_quantity(item) == (Decimal("12"), QUANTITY_FROM_COMMERCIAL)


def test_package_with_taxable_unit_in_units_is_converted():
    """Display de 30 unidades: a nota informa qTrib em UNI, logo o fator vem do documento."""
    item = {"u_com": "EXB", "q_com": "1", "u_trib": "UNI", "q_trib": "30"}

    assert resolve_sale_unit_quantity(item) == (Decimal("30"), QUANTITY_FROM_TAXABLE)


def test_multiple_packages_multiply_the_units():
    item = {"u_com": "EXB", "q_com": "2", "u_trib": "UNI", "q_trib": "60"}

    assert resolve_sale_unit_quantity(item) == (Decimal("60"), QUANTITY_FROM_TAXABLE)


def test_weight_as_taxable_unit_is_not_convertible():
    """Caixa cobrada em quilos nao diz quantas unidades de venda existem."""
    item = {"u_com": "CX", "q_com": "1", "u_trib": "KG", "q_trib": "3.6"}

    assert resolve_sale_unit_quantity(item) == (Decimal("0"), None)


def test_package_repeated_as_taxable_unit_is_not_convertible():
    item = {"u_com": "CX12", "q_com": "1", "u_trib": "CX12", "q_trib": "1"}

    assert resolve_sale_unit_quantity(item) == (Decimal("0"), None)


def test_zero_taxable_quantity_is_not_convertible():
    item = {"u_com": "DP", "q_com": "1", "u_trib": "UNI", "q_trib": "0"}

    assert resolve_sale_unit_quantity(item) == (Decimal("0"), None)


def test_cost_uses_converted_quantity():
    item = {
        "u_com": "EXB",
        "q_com": "1",
        "u_trib": "UNI",
        "q_trib": "30",
        "v_prod": "60.00",
    }

    computed = compute_unit_cost(item, _totals("60.00"))

    assert computed["quantidade"] == Decimal("30")
    assert computed["quantidade_origem"] == QUANTITY_FROM_TAXABLE
    assert computed["preco_custo"] == Decimal("2.0000")


def test_unconvertible_item_falls_back_without_claiming_conversion():
    """O calculo segue para o relatorio, mas sem afirmar que a unidade foi resolvida."""
    item = {"u_com": "CX", "q_com": "1", "u_trib": "KG", "q_trib": "3.6", "v_prod": "60.00"}

    computed = compute_unit_cost(item, _totals("60.00"))

    assert computed["quantidade"] == Decimal("1")
    assert computed["quantidade_origem"] is None
