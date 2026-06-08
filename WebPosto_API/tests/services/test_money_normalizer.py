from decimal import Decimal

from src.services.money_normalizer import (
    normalize_cents,
    normalize_webposto_account_value,
    normalize_webposto_expense_value,
    normalize_webposto_money,
    normalize_webposto_sale_value,
    parse_decimal_br,
)
from src.services.network_financial_overview_service import NetworkFinancialOverviewService


def test_parse_decimal_br_formats():
    assert parse_decimal_br("1648.29") == Decimal("1648.29")
    assert parse_decimal_br("1648,29") == Decimal("1648.29")
    assert parse_decimal_br("13.200,00") == Decimal("13200.00")


def test_normalize_cents_integer_input():
    assert normalize_cents(164829) == Decimal("1648.29")
    assert normalize_cents("313000") == Decimal("3130.00")


def test_normalize_webposto_money_mixed_inputs():
    assert normalize_webposto_money("164829") == Decimal("1648.29")
    assert normalize_webposto_money("1320,00") == Decimal("1320.00")
    assert normalize_webposto_money("13.200,00") == Decimal("13200.00")


def test_context_normalizers_preserve_decimal_for_webposto_endpoints():
    assert normalize_webposto_expense_value(1648.29) == Decimal("1648.29")
    assert normalize_webposto_account_value("3130.00") == Decimal("3130.00")
    assert normalize_webposto_sale_value("9876,54") == Decimal("9876.54")


def test_real_problematic_expenses_values_remain_correct():
    assert normalize_webposto_expense_value(1648.29) == Decimal("1648.29")
    assert (
        normalize_webposto_expense_value(1130.0)
        + normalize_webposto_expense_value(2000.0)
        == Decimal("3130.00")
    )
    assert (
        normalize_webposto_expense_value(720.0)
        + normalize_webposto_expense_value(600.0)
        == Decimal("1320.00")
    )


def test_deduplicate_rows_by_business_keys():
    rows = [
        {
            "empresaCodigo": 5555,
            "data": "2026-06-05",
            "valor": "1648.29",
            "planoConta": "ref ao abastecimento do caminhao",
            "tipoDespesa": "",
            "centroCusto": "",
            "origem": "financeiro",
            "status": "pago",
        },
        {
            "empresaCodigo": 5555,
            "data": "2026-06-05",
            "valor": "1648.29",
            "planoConta": "ref ao abastecimento do caminhao",
            "tipoDespesa": "",
            "centroCusto": "",
            "origem": "financeiro",
            "status": "pago",
        },
    ]

    deduped = NetworkFinancialOverviewService._dedupe_rows(
        rows,
        keys=(
            "empresaCodigo",
            "data",
            "valor",
            "planoConta",
            "tipoDespesa",
            "centroCusto",
            "origem",
            "status",
        ),
    )

    assert len(deduped) == 1
