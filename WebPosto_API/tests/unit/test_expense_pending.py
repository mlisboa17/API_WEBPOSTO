"""Testes de tratativa de despesas pendentes — Sprint 44."""

from src.services.expense_pending_service import (
    ExpensePendingService,
    ExpensePendingSummary,
)
from src.domain.enums.expense_classification import (
    ExpenseClassification,
    ExpenseClassificationStatus,
)


def test_group_pending_expenses_creates_summary():
    service = ExpensePendingService()
    expenses = [
        {
            "id": "1",
            "empresaCodigo": 11495,
            "empresaNome": "Posto VIP",
            "planoContasCodigo": "1.01",
            "planoContasDescricao": "Despesas Operacionais",
            "valor": 1000.00,
        },
        {
            "id": "2",
            "empresaCodigo": 11495,
            "planoContasCodigo": "1.01",
            "valor": 500.00,
        },
        {
            "id": "3",
            "empresaCodigo": 5555,
            "planoContasCodigo": "2.01",
            "valor": 2000.00,
        },
    ]

    summary = service.group_pending_expenses(expenses)

    assert isinstance(summary, ExpensePendingSummary)
    assert summary.total_pending_count == 3
    assert summary.total_pending_value == 3500.00
    assert len(summary.groups) == 2
    assert summary.by_company[11495] == 1500.00
    assert summary.by_company[5555] == 2000.00


def test_pending_expenses_block_dre_when_above_threshold():
    service = ExpensePendingService()
    expenses = [
        {"id": "1", "empresaCodigo": 11495, "planoContasCodigo": "1.01", "valor": 5000.00},
    ]
    revenues = {11495: 100000.00}

    summary = service.group_pending_expenses(expenses, company_revenues=revenues)

    assert summary.blocks_dre is True


def test_pending_expenses_do_not_block_dre_below_threshold():
    service = ExpensePendingService()
    expenses = [
        {"id": "1", "empresaCodigo": 11495, "planoContasCodigo": "1.01", "valor": 100.00},
    ]
    revenues = {11495: 100000.00}

    summary = service.group_pending_expenses(expenses, company_revenues=revenues)

    assert summary.blocks_dre is False


def test_inject_pending_center_in_dre():
    service = ExpensePendingService()
    dre_lines = [
        {"companyCode": 11495, "department": "combustiveis", "expenses": "1000"},
    ]
    expenses = [
        {"id": "1", "empresaCodigo": 11495, "planoContasCodigo": "1.01", "valor": 500.00},
    ]
    summary = service.group_pending_expenses(expenses)

    result = service.inject_pending_center_in_dre(dre_lines, summary)

    assert len(result) == 2
    pending_line = next(l for l in result if l.get("isPendingClassification"))
    assert pending_line["companyCode"] == 11495
    assert pending_line["status"] == "PENDENTE_CLASSIFICACAO"
    assert pending_line["expenses"] == "500.0"


def test_expense_classification_from_plano_contas():
    assert ExpenseClassification.from_plano_contas("1.01") == ExpenseClassification.OPERACIONAL
    assert ExpenseClassification.from_plano_contas("2.01") == ExpenseClassification.ADMINISTRATIVA
    assert ExpenseClassification.from_plano_contas("3.01") == ExpenseClassification.PESSOAL
    assert ExpenseClassification.from_plano_contas("4.01") == ExpenseClassification.TRIBUTARIA
    assert ExpenseClassification.from_plano_contas("5.01") == ExpenseClassification.FINANCEIRA
    assert ExpenseClassification.from_plano_contas("9.99") == ExpenseClassification.PENDENTE
    assert ExpenseClassification.from_plano_contas(None) == ExpenseClassification.PENDENTE
