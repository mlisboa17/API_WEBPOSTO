"""Testes unitários — Management Classification & Employee Cash Ledger (F03.3)."""
from __future__ import annotations

import pytest

from src.services.employee_cash_ledger_service import EmployeeCashLedgerService
from src.services.expense_semantic_service import ExpenseSemanticService
from src.services.management_classification_service import ManagementClassificationService
from src.services.network_financial_overview_service import FinancialOverviewFilters


@pytest.mark.parametrize(
    ("row", "expected_group", "expected_class", "expected_dre"),
    [
        (
            {"expenseNature": "ADIANTAMENTO", "expenseSubNature": "VALE_FUNCIONARIO", "descricao": "VALE"},
            "TESOURARIA",
            "VALE",
            "NAO",
        ),
        (
            {"expenseNature": "DESPESA_FINANCEIRA", "expenseSubNature": "ENERGIA", "descricao": "ENERGIA"},
            "ADMINISTRATIVO",
            "ENERGIA",
            "SIM",
        ),
        (
            {"expenseNature": "AJUSTE_OPERACIONAL", "expenseSubNature": "QUEBRA_DE_CAIXA", "descricao": "QUEBRA"},
            "PERDAS",
            "PERDA_CAIXA_FUNCIONARIO",
            "NAO",
        ),
    ],
)
def test_management_classify_row(row, expected_group, expected_class, expected_dre) -> None:
    semantic = ExpenseSemanticService()
    base = semantic.classify_row(row) if "expenseNature" not in row else row
    svc = ManagementClassificationService()
    out = svc.classify_row(base)
    assert out["expenseManagementGroup"] == expected_group
    assert out["expenseManagementClass"] == expected_class
    assert out["dreImpact"] == expected_dre
    assert out.get("expenseNature") == row.get("expenseNature") or out.get("expenseNature")


def test_balance_engine_compensation() -> None:
    ledger = EmployeeCashLedgerService()
    caixa_events = [
        {"eventType": "FALTA_CAIXA", "funcionarioCodigo": 100, "valor": 50.0},
        {"eventType": "SOBRA_CAIXA", "funcionarioCodigo": 100, "valor": 30.0},
    ]
    balance = ledger.build_balance_by_operator(caixa_events, [])
    op = balance[100]
    assert op["saldo"] == -20.0
    assert op["compensadoAutomatico"] == 30.0
    assert op["classificacao"] == "DEVEDOR"


def test_filter_by_management_group() -> None:
    svc = ManagementClassificationService()
    rows = [
        svc.classify_row({"expenseNature": "ADIANTAMENTO", "expenseSubNature": "VALE_FUNCIONARIO", "valor": 10}),
        svc.classify_row({"expenseNature": "DESPESA_FINANCEIRA", "expenseSubNature": "ENERGIA", "valor": 20}),
    ]
    filters = FinancialOverviewFilters(
        data_inicial="2026-01-01",
        data_final="2026-01-31",
        expense_management_groups=("TESOURARIA",),
    )
    filtered = svc.filter_rows(rows, filters)
    assert len(filtered) == 1
    assert filtered[0]["expenseManagementGroup"] == "TESOURARIA"


def test_forensics_saldo_liquido() -> None:
    ledger = EmployeeCashLedgerService()
    events = [
        {"eventType": "FALTA_CAIXA", "valor": 100.0},
        {"eventType": "SOBRA_CAIXA", "valor": 40.0},
    ]
    summary = ledger.summarize_forensics(events)
    assert summary["faltasCount"] == 1
    assert summary["sobrasCount"] == 1
    assert summary["saldoLiquidoRede"] == -60.0
