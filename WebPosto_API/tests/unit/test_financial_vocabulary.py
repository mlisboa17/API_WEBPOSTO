from src.core.financial_vocabulary import (
    FinancialConcept,
    Impact,
    financial_vocabulary_entry,
)


def test_cash_withdrawal_is_not_an_expense_or_cash_loss() -> None:
    entry = financial_vocabulary_entry(FinancialConcept.CASH_WITHDRAWAL)

    assert entry.direct_evidence is False
    assert entry.affects_dre == Impact.NO
    assert entry.affects_cash == Impact.NO


def test_cash_supply_is_not_revenue() -> None:
    entry = financial_vocabulary_entry(FinancialConcept.CASH_SUPPLY)

    assert entry.webposto_fields == ("suprimentoCaixa",)
    assert entry.affects_dre == Impact.NO


def test_cash_register_expense_requires_dre_reconciliation() -> None:
    entry = financial_vocabulary_entry(FinancialConcept.CASH_REGISTER_EXPENSE)

    assert entry.affects_cash == Impact.YES
    assert entry.affects_dre == Impact.DEPENDS_ON_RECONCILIATION


def test_account_payable_is_not_automatically_a_realized_expense() -> None:
    entry = financial_vocabulary_entry(FinancialConcept.ACCOUNT_PAYABLE)

    assert "situacao" in entry.webposto_fields
    assert entry.affects_dre == Impact.DEPENDS_ON_RECONCILIATION
