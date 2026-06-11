"""Testes unitários — Prestação de Contas F03.4-B."""
from __future__ import annotations

from src.services.prestacao_contas_intelligence_service import PrestacaoContasIntelligenceService


def test_discovery_catalog():
    report = PrestacaoContasIntelligenceService.discovery_report()
    assert report["onlyInPrestacao"]
    assert "funcionarioNome" in report["onlyInPrestacao"]
    assert "fundoCaixa" in report["onlyInPrestacao"]
    assert len(report["answers"]["1_camposApenasPrestacao"]) >= 4


def test_vale_forensics_classification():
    enriched = [
        {"descricao": "VALE FUNCIONARIO JOAO", "valor": 50, "expenseManagementClass": "VALE", "expenseNature": "ADIANTAMENTO"},
        {"descricao": "EMPRESTIMO FUNC", "valor": 100, "expenseManagementClass": "EMPRESTIMO"},
    ]
    report = PrestacaoContasIntelligenceService.vale_forensics(enriched)
    assert report["total"] == 2
    assert report["valorTotal"] == 150.0


def test_cash_expense_origin_bobina():
    enriched = [
        {"descricao": "BOBINA TERMICA", "valor": 12.5, "expenseManagementClass": "BOBINA", "origem": "financeiro"},
    ]
    report = PrestacaoContasIntelligenceService.cash_expense_origin(enriched)
    assert report["bobinaTermica"]["count"] == 1
    assert report["totals"].get("DESPESA_OPERACIONAL") == 12.5
