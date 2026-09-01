"""Testes do motor de cruzamento cartão x banco (D02+)."""
from __future__ import annotations

from datetime import datetime

from src.domain.reconciliation.bank_statement import BankTransaction, BankTransactionCategory
from src.services.bank_reconciliation.card_bank_matching_service import (
    CardSaleEvent,
    compare_daily_card_settlements,
    compare_daily_card_settlements_with_lag,
    extract_premmia_settlements,
    match_card_settlements,
)


def _bank_txn(**overrides) -> BankTransaction:
    defaults = dict(
        bankId="290",
        acctId="00000000-0",
        fitId="fitid-1",
        trnType="IN",
        postedAt=datetime(2026, 7, 1, 10, 0, 0),
        amount=100.0,
        memo="Vendas - Disponivel CREDITO VISA",
        category=BankTransactionCategory.CARD_SETTLEMENT,
        cardMethod="CREDITO",
        cardBrand="VISA",
    )
    defaults.update(overrides)
    return BankTransaction(**defaults)


def test_match_card_settlements_exact_amount():
    sale = CardSaleEvent(reference="v1", occurredAt=datetime(2026, 7, 1, 9, 0), amount=100.0, brand="VISA", method="CREDITO")
    bank_txn = _bank_txn(amount=100.0)

    result = match_card_settlements([sale], [bank_txn])

    assert len(result.matched) == 1
    assert result.matched[0].delta == 0.0
    assert result.unmatchedSales == []
    assert result.unmatchedBankTransactions == []


def test_match_card_settlements_within_tolerance():
    sale = CardSaleEvent(reference="v1", occurredAt=datetime(2026, 7, 1, 9, 0), amount=100.0, brand="VISA", method="CREDITO")
    bank_txn = _bank_txn(amount=100.03)

    result = match_card_settlements([sale], [bank_txn], amount_tolerance=0.05)

    assert len(result.matched) == 1
    assert result.matched[0].delta == 0.03


def test_match_card_settlements_brand_mismatch_stays_unmatched():
    sale = CardSaleEvent(reference="v1", occurredAt=datetime(2026, 7, 1, 9, 0), amount=100.0, brand="MASTERCARD", method="CREDITO")
    bank_txn = _bank_txn(amount=100.0, cardBrand="VISA")

    result = match_card_settlements([sale], [bank_txn])

    assert result.matched == []
    assert result.unmatchedSales == [sale]
    assert result.unmatchedBankTransactions == [bank_txn]


def test_match_card_settlements_outside_date_window():
    sale = CardSaleEvent(reference="v1", occurredAt=datetime(2026, 7, 1, 9, 0), amount=100.0, brand="VISA", method="CREDITO")
    bank_txn = _bank_txn(amount=100.0, postedAt=datetime(2026, 7, 5, 9, 0))

    result = match_card_settlements([sale], [bank_txn], date_window_days=1)

    assert result.matched == []
    assert result.unmatchedSales == [sale]
    assert result.unmatchedBankTransactions == [bank_txn]


def test_match_card_settlements_greedy_prefers_closest_amount():
    sale = CardSaleEvent(reference="v1", occurredAt=datetime(2026, 7, 1, 9, 0), amount=100.0, brand="VISA", method="CREDITO")
    close_txn = _bank_txn(fitId="close", amount=99.98)
    far_txn = _bank_txn(fitId="far", amount=90.0)

    result = match_card_settlements([sale], [close_txn, far_txn], amount_tolerance=1.0)

    assert len(result.matched) == 1
    assert result.matched[0].bankTransaction.fitId == "close"
    assert result.unmatchedBankTransactions == [far_txn]


def test_extract_premmia_settlements_filters_vibra_pix():
    premmia_pix = BankTransaction(
        bankId="290",
        acctId="00000000-0",
        fitId="fitid-pix",
        trnType="IN",
        postedAt=datetime(2026, 7, 3, 14, 0),
        amount=502.06,
        memo="Pix recebido - Vibra Energia S.a",
        category=BankTransactionCategory.PIX_RECEIVED,
        counterparty="Vibra Energia S.a",
        likelyPremmia=True,
    )
    other_pix = BankTransaction(
        bankId="290",
        acctId="00000000-0",
        fitId="fitid-pix2",
        trnType="IN",
        postedAt=datetime(2026, 7, 3, 15, 0),
        amount=2000.0,
        memo="Pix recebido - Auto Posto Exemplo Ltda",
        category=BankTransactionCategory.PIX_RECEIVED,
        counterparty="Auto Posto Exemplo Ltda",
        likelyPremmia=False,
    )

    result = extract_premmia_settlements([premmia_pix, other_pix])

    assert result == [premmia_pix]


def test_match_card_settlements_accepts_credit_trntype_convention():
    """Itaú usa TRNTYPE=CREDIT/DEBIT (não IN/OUT como o PagBank)."""
    sale = CardSaleEvent(reference="v1", occurredAt=datetime(2026, 7, 10, 9, 0), amount=2546.88, brand="VISA", method="CREDITO")
    bank_txn = _bank_txn(amount=2546.88, trnType="CREDIT", acquirer="REDE", settlementCode="AT", postedAt=datetime(2026, 7, 10, 10, 0))

    result = match_card_settlements([sale], [bank_txn])

    assert len(result.matched) == 1


def test_compare_daily_card_settlements_matches_bucket_totals():
    sale_1 = CardSaleEvent(reference="v1", occurredAt=datetime(2026, 7, 10, 9, 0), amount=1500.0, brand="VISA", method="CREDITO")
    sale_2 = CardSaleEvent(reference="v2", occurredAt=datetime(2026, 7, 10, 15, 0), amount=1046.88, brand="VISA", method="CREDITO")
    bank_txn = _bank_txn(amount=2546.88, trnType="CREDIT", acquirer="REDE", settlementCode="AT", postedAt=datetime(2026, 7, 10, 10, 0))

    comparisons = compare_daily_card_settlements([sale_1, sale_2], [bank_txn])

    assert len(comparisons) == 1
    bucket = comparisons[0]
    assert bucket.salesTotal == 2546.88
    assert bucket.bankTotal == 2546.88
    assert bucket.delta == 0.0


def test_compare_daily_card_settlements_reports_bucket_without_bank_entry():
    sale = CardSaleEvent(reference="v1", occurredAt=datetime(2026, 7, 11, 9, 0), amount=100.0, brand="ELO", method="DEBITO")

    comparisons = compare_daily_card_settlements([sale], [])

    assert len(comparisons) == 1
    assert comparisons[0].bankTotal is None
    assert comparisons[0].delta is None
    assert comparisons[0].salesTotal == 100.0


def test_compare_daily_card_settlements_reports_bucket_without_sales():
    bank_txn = _bank_txn(amount=200.0, trnType="CREDIT", acquirer="CIELO", settlementCode="DB", postedAt=datetime(2026, 7, 11, 10, 0))

    comparisons = compare_daily_card_settlements([], [bank_txn])

    assert len(comparisons) == 1
    assert comparisons[0].salesTotal == 0.0
    assert comparisons[0].bankTotal == 200.0
    assert comparisons[0].delta == 200.0


def test_compare_daily_card_settlements_with_lag_shifts_rede_credit_to_previous_business_day():
    # REDE deposita em D+1 util: venda de sexta (2026-07-10) casa com credito bancario de segunda
    # (2026-07-13), pois sabado/domingo nao contam como dia util.
    sale = CardSaleEvent(reference="v1", occurredAt=datetime(2026, 7, 10, 9, 0), amount=500.0, brand="VISA", method="CREDITO")
    bank_txn = _bank_txn(amount=500.0, trnType="CREDIT", acquirer="REDE", postedAt=datetime(2026, 7, 13, 10, 0))

    comparisons = compare_daily_card_settlements_with_lag(
        [sale], [bank_txn], acquirer_lag_business_days={"REDE": 1}
    )

    assert len(comparisons) == 1
    bucket = comparisons[0]
    assert bucket.settlementDate == sale.occurredAt.date()
    assert bucket.salesTotal == 500.0
    assert bucket.bankTotal == 500.0
    assert bucket.delta == 0.0


def test_compare_daily_card_settlements_with_lag_defaults_to_same_day_for_unlisted_acquirer():
    sale = CardSaleEvent(reference="v1", occurredAt=datetime(2026, 7, 10, 9, 0), amount=200.0, brand="VISA", method="CREDITO")
    bank_txn = _bank_txn(amount=200.0, trnType="CREDIT", acquirer="CIELO", postedAt=datetime(2026, 7, 10, 10, 0))

    comparisons = compare_daily_card_settlements_with_lag(
        [sale], [bank_txn], acquirer_lag_business_days={"REDE": 1}
    )

    assert len(comparisons) == 1
    assert comparisons[0].delta == 0.0
