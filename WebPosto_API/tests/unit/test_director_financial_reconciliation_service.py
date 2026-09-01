from datetime import date
from decimal import Decimal

from src.core.financial_vocabulary import FinancialConcept
from src.domain.financial_reconciliation import FinancialFact, FinancialSource, MatchStatus
from src.services.director_financial_reconciliation_service import DirectorFinancialReconciliationService


def fact(fact_id: str, source: FinancialSource, concept: FinancialConcept, **values) -> FinancialFact:
    return FinancialFact(
        fact_id=fact_id,
        source=source,
        concept=concept,
        company_code=11495,
        effective_date=date(2026, 7, 1),
        amount=Decimal("100.00"),
        **values,
    )


def test_exact_cross_source_match_with_account_is_confirmed() -> None:
    result = DirectorFinancialReconciliationService().reconcile([
        fact("expense", FinancialSource.EXPENSES, FinancialConcept.FINANCIAL_EXPENSE,
             management_account_code="42", department="Combustiveis"),
        fact("cash", FinancialSource.CASH_EXPENSE, FinancialConcept.CASH_REGISTER_EXPENSE,
             management_account_code="42"),
    ], complete_source_coverage=True)
    assert result.matches[0].status == MatchStatus.CONFIRMED
    assert result.matches[0].may_enter_dre is True


def test_same_amount_without_reference_is_only_probable() -> None:
    result = DirectorFinancialReconciliationService().reconcile([
        fact("expense", FinancialSource.EXPENSES, FinancialConcept.FINANCIAL_EXPENSE,
             department="Combustiveis"),
        fact("payable", FinancialSource.PAYABLE, FinancialConcept.ACCOUNT_PAYABLE),
    ], complete_source_coverage=True)
    assert result.matches[0].status == MatchStatus.PROBABLE
    assert result.matches[0].may_enter_dre is False


def test_unclassified_expense_goes_to_quarantine() -> None:
    result = DirectorFinancialReconciliationService().reconcile(
        [fact("expense", FinancialSource.EXPENSES, FinancialConcept.FINANCIAL_EXPENSE)],
        complete_source_coverage=True,
    )
    assert result.matches[0].status == MatchStatus.QUARANTINED


def test_incomplete_coverage_blocks_executive_totals() -> None:
    result = DirectorFinancialReconciliationService().reconcile([], complete_source_coverage=False)
    assert result.complete_source_coverage is False
    assert "bloqueados" in result.warnings[0]


def test_same_source_duplicate_is_not_counted_as_match() -> None:
    item = fact("expense-1", FinancialSource.EXPENSES, FinancialConcept.FINANCIAL_EXPENSE,
                document="NF 1", department="Conveniencia")
    duplicate = item.model_copy(update={"fact_id": "expense-2"})
    result = DirectorFinancialReconciliationService().reconcile(
        [item, duplicate], complete_source_coverage=True
    )
    assert result.matches[0].status == MatchStatus.DUPLICATE
    assert result.matches[0].may_enter_dre is False
