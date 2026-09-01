"""Testes de impacto das taxas de cartão — Sprint 48."""

from src.services.card_fee_impact_service import (
    CardFeeImpactService,
    CardFeeImpactSummary,
    CardBrandFee,
    DEFAULT_CARD_FEES,
)


def test_calculate_fee_with_default_rate():
    service = CardFeeImpactService()

    result = service.calculate_fee(1000.0, "VISA", "CREDITO")

    assert result["valor_bruto"] == 1000.0
    assert result["taxa_percentual"] == 2.49
    assert result["valor_taxa"] == 24.90
    assert result["valor_liquido"] == 975.10


def test_calculate_fee_with_webposto_rate():
    service = CardFeeImpactService()

    result = service.calculate_fee(1000.0, "VISA", "CREDITO", taxa_percentual=2.00)

    assert result["taxa_percentual"] == 2.00
    assert result["valor_taxa"] == 20.00
    assert result["valor_liquido"] == 980.00


def test_calculate_fee_debito_lower_rate():
    service = CardFeeImpactService()

    result_cred = service.calculate_fee(1000.0, "VISA", "CREDITO")
    result_deb = service.calculate_fee(1000.0, "VISA", "DEBITO")

    assert result_cred["taxa_percentual"] > result_deb["taxa_percentual"]
    assert result_deb["valor_taxa"] == 14.90


def test_analyze_card_sales_single_brand():
    service = CardFeeImpactService()

    transactions = [
        {"bandeira": "VISA", "metodo": "CREDITO", "valor": 10000.0},
        {"bandeira": "VISA", "metodo": "CREDITO", "valor": 5000.0},
    ]

    summary = service.analyze_card_sales(
        transactions, "2026-07-01", "2026-07-31", empresa_codigo=11495
    )

    assert summary.receita_bruta_cartoes == 15000.0
    assert summary.total_taxas_cartao_rs == 15000 * 0.0249
    assert len(summary.by_brand) == 1


def test_analyze_card_sales_multiple_brands():
    service = CardFeeImpactService()

    transactions = [
        {"bandeira": "VISA", "metodo": "CREDITO", "valor": 10000.0},
        {"bandeira": "MASTERCARD", "metodo": "DEBITO", "valor": 8000.0},
        {"bandeira": "ELO", "metodo": "CREDITO", "valor": 5000.0},
    ]

    summary = service.analyze_card_sales(
        transactions, "2026-07-01", "2026-07-31"
    )

    assert summary.receita_bruta_cartoes == 23000.0
    assert len(summary.by_brand) == 3
    assert summary.taxa_media_ponderada_pct > 0


def test_analyze_with_margin_calculation():
    service = CardFeeImpactService()

    transactions = [
        {"bandeira": "VISA", "metodo": "CREDITO", "valor": 100000.0},
    ]

    summary = service.analyze_card_sales(
        transactions,
        "2026-07-01",
        "2026-07-31",
        receita_total=150000.0,
        cmv_total=120000.0,
    )

    assert summary.receita_total == 150000.0
    assert summary.cmv_total == 120000.0
    assert summary.margem_bruta == 30000.0
    assert summary.margem_bruta_pct == 20.0
    assert summary.margem_liquida_pos_cartoes < summary.margem_bruta


def test_impacto_taxas_na_margem():
    service = CardFeeImpactService()

    transactions = [
        {"bandeira": "VISA", "metodo": "CREDITO", "valor": 100000.0, "taxaPercentual": 2.5},
    ]

    summary = service.analyze_card_sales(
        transactions,
        "2026-07-01",
        "2026-07-31",
        receita_total=100000.0,
        cmv_total=80000.0,
    )

    assert summary.margem_bruta == 20000.0
    assert summary.total_taxas_cartao_rs == 2500.0
    assert summary.margem_liquida_pos_cartoes == 17500.0
    assert summary.impacto_taxas_na_margem_pct == 12.5


def test_by_method_aggregation():
    service = CardFeeImpactService()

    transactions = [
        {"bandeira": "VISA", "metodo": "CREDITO", "valor": 50000.0},
        {"bandeira": "MASTERCARD", "metodo": "CREDITO", "valor": 30000.0},
        {"bandeira": "VISA", "metodo": "DEBITO", "valor": 20000.0},
    ]

    summary = service.analyze_card_sales(transactions, "2026-07-01", "2026-07-31")

    assert "CREDITO" in summary.by_method
    assert "DEBITO" in summary.by_method
    assert summary.by_method["CREDITO"] == 80000.0
    assert summary.by_method["DEBITO"] == 20000.0


def test_calculate_margin_after_fees():
    service = CardFeeImpactService()

    result = service.calculate_margin_after_fees(
        receita=100000.0,
        cmv=75000.0,
        total_taxas_cartao=2000.0,
    )

    assert result["margem_bruta"] == 25000.0
    assert result["margem_bruta_pct"] == 25.0
    assert result["margem_liquida"] == 23000.0
    assert result["margem_liquida_pct"] == 23.0


def test_custom_fees_configuration():
    custom_fees = {
        "VISA": {"CREDITO": 1.99, "DEBITO": 0.99},
        "DEFAULT": {"CREDITO": 2.00, "DEBITO": 1.00},
    }
    service = CardFeeImpactService(custom_fees=custom_fees)

    result = service.calculate_fee(1000.0, "VISA", "CREDITO")

    assert result["taxa_percentual"] == 1.99
