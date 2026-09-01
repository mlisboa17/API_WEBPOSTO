from decimal import Decimal

from src.services.fuel_sales_contract_service import FuelSalesContractService


def fuel_row(**overrides):
    row = {
        "empresaCodigo": 11495,
        "vendaCodigo": 360031677,
        "vendaItemCodigo": 747220348,
        "produtoCodigo": 1257884,
        "produtoLmcCodigo": 8297,
        "bicoCodigo": 42902,
        "tanqueCodigo": 100,
        "dataMovimento": "2026-07-01",
        "quantidade": "10.5555",
        "precoVenda": "6.25",
        "precoCusto": "5.10",
        "totalVenda": "65.97",
        "totalCusto": "53.83",
    }
    row.update(overrides)
    return row


def test_normalizes_real_fuel_sale_fields() -> None:
    fact = FuelSalesContractService.normalize_item(fuel_row())

    assert fact.departamento == "combustiveis"
    assert fact.litros == Decimal("10.556")
    assert fact.faturamento == Decimal("65.970")
    assert fact.empresa_codigo == 11495


def test_group_24554_is_sufficient_evidence_without_lmc_fields() -> None:
    fact = FuelSalesContractService.normalize_item(
        fuel_row(produtoLmcCodigo=None, bicoCodigo=None, tanqueCodigo=None),
        group_by_product={1257884: 24554},
    )

    assert fact.grupo_codigo == 24554


def test_batch_quarantines_items_without_fuel_evidence() -> None:
    result = FuelSalesContractService.normalize_batch(
        [fuel_row(), fuel_row(vendaItemCodigo=2, produtoLmcCodigo=None, bicoCodigo=None, tanqueCodigo=None)]
    )

    assert len(result["accepted"]) == 1
    assert len(result["quarantine"]) == 1


def test_batch_removes_duplicate_business_key() -> None:
    row = fuel_row()
    result = FuelSalesContractService.normalize_batch([row, dict(row)])

    assert result["duplicates"] == 1
    assert len(result["accepted"]) == 1
