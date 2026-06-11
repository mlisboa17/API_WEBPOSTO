"""Testes unitários — Expense Semantic Intelligence (F03.2)."""
from __future__ import annotations

import pytest

from src.services.expense_semantic_service import ExpenseSemanticService
from src.services.network_financial_overview_service import FinancialOverviewFilters


@pytest.mark.parametrize(
    ("row", "expected_nature", "expected_sub"),
    [
        (
            {"origem": "financeiro", "descricao": "BOBINA TERMICA", "planoConta": "BOBINA TERMICA"},
            "DESPESA_FINANCEIRA",
            "BOBINA_TERMICA",
        ),
        (
            {"origem": "pdv", "descricao": "Vale de funcionário referente a consolidação de caixa"},
            "ADIANTAMENTO",
            "VALE_FUNCIONARIO",
        ),
        (
            {"origem": "pdv", "descricao": "TROCO INICIAL", "eventoOperacional": "Troco Inicial"},
            "MOVIMENTACAO_CAIXA",
            "TROCO",
        ),
        (
            {"origem": "pdv", "descricao": "FUNDO DE CAIXA", "eventoOperacional": "Fundo de Caixa"},
            "MOVIMENTACAO_CAIXA",
            "FUNDO_DE_CAIXA",
        ),
        (
            {"origem": "pdv", "descricao": "LIMPEZA DO POSTO"},
            "DESPESA_OPERACIONAL",
            "LIMPEZA",
        ),
        (
            {"origem": "pdv", "descricao": "QUEBRA DE CAIXA", "eventoOperacional": "Quebra de Caixa"},
            "AJUSTE_OPERACIONAL",
            "QUEBRA_DE_CAIXA",
        ),
    ],
)
def test_classify_row_mandatory_cases(row, expected_nature, expected_sub) -> None:
    svc = ExpenseSemanticService()
    out = svc.classify_row(row)
    assert out["expenseNature"] == expected_nature
    assert out["expenseSubNature"] == expected_sub
    assert out.get("semanticConfidence", 0) >= 75


def test_summarize_classification_pct() -> None:
    svc = ExpenseSemanticService()
    rows = [
        svc.classify_row({"origem": "financeiro", "descricao": "ENERGIA", "valor": 100}),
        svc.classify_row({"origem": "pdv", "descricao": "VALE FUNCIONARIO", "valor": 50}),
    ]
    summary = svc.summarize(rows)
    assert summary["totalRecords"] == 2
    assert summary["unclassifiedRecords"] == 0
    assert summary["classificationPct"] == 100.0


def test_filter_by_natures() -> None:
    svc = ExpenseSemanticService()
    rows = [
        {"expenseNature": "DESPESA_FINANCEIRA", "valor": 1},
        {"expenseNature": "ADIANTAMENTO", "valor": 2},
    ]
    filters = FinancialOverviewFilters("2026-06-01", "2026-06-07", expense_natures=("DESPESA_FINANCEIRA",))
    filtered = svc.filter_by_natures(rows, filters)
    assert len(filtered) == 1
    assert filtered[0]["expenseNature"] == "DESPESA_FINANCEIRA"
