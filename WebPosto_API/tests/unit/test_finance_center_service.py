"""Testes F01 — Centro Financeiro Corporativo."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.response_model import WebPostoResponse
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.logos_expense_classifier import classify_logos_expense
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService


def test_classify_logos_expense() -> None:
    assert classify_logos_expense("Vale de funcionário", "") == "PESSOAL"
    assert classify_logos_expense("AGUA PARA CONSUMO", "") == "OPERACIONAL"
    assert classify_logos_expense("pagamento alamoa", "") == "OUTROS"


def test_payables_buckets() -> None:
    service = CorporateFinanceCenterService(MagicMock())
    rows = [
        {"situacao": "Pago", "valor": 100, "vencimento": "2026-06-01", "dataPagamento": "2026-06-02"},
        {"situacao": "Aberto", "valor": 50, "vencimento": "2026-05-01"},
        {"situacao": "Aberto", "valor": 30, "vencimento": "2026-06-10"},
    ]
    buckets = service._classify_payables(rows, "2026-06-07")
    assert len(buckets["pago"]) == 1
    assert len(buckets["emAberto"]) == 2
    assert len(buckets["vencido"]) == 1
    assert len(buckets["aVencer"]) == 1


def test_summary_payload_has_no_merged_total() -> None:
    """Summary não deve expor totalFinanceiro misturando fontes."""
    sample = {
        "despesasGerenciais": {"totalValor": "100"},
        "contasPagar": {"emAberto": {"valor": "200"}},
        "movimentoBancario": {"saldoMovimentado": {"liquido": "50"}},
    }
    assert "totalFinanceiro" not in sample


@pytest.mark.asyncio
async def test_get_expenses_multiselect_single_fetch() -> None:
    overview = NetworkFinancialOverviewService(MagicMock())
    overview._load_filtered_expenses = AsyncMock(
        return_value=(
            [
                {
                    "empresaCodigo": 11495,
                    "data": "2026-06-01",
                    "valor": "10",
                    "planoConta": "vale",
                    "raw": {"descricaoDocumento": "Vale"},
                },
                {
                    "empresaCodigo": 5555,
                    "data": "2026-06-01",
                    "valor": "20",
                    "planoConta": "x",
                    "raw": {"descricaoDocumento": "x"},
                },
            ],
            None,
        )
    )
    service = CorporateFinanceCenterService(overview)
    filters = FinancialOverviewFilters(
        data_inicial="2026-06-01",
        data_final="2026-06-07",
        empresa_codigos=(11495, 5555),
    )
    resp = await service.get_expenses(filters, "11495,5555")
    assert resp.success
    assert resp.data["resumo"]["totalRegistros"] == 2
    assert all(r["categoriaLogos"] for r in resp.data["data"])


@pytest.mark.asyncio
async def test_get_payables_single_fetch() -> None:
    client = MagicMock()
    overview = NetworkFinancialOverviewService(client)
    client.call_endpoint = AsyncMock(
        return_value=WebPostoResponse.ok(
            [
                {"empresaCodigo": 11495, "situacao": "Aberto", "valor": 10, "vencimento": "2026-06-05"},
                {"empresaCodigo": 5555, "situacao": "Aberto", "valor": 20, "vencimento": "2026-06-05"},
            ]
        )
    )
    service = CorporateFinanceCenterService(overview)
    filters = FinancialOverviewFilters(
        data_inicial="2026-06-01",
        data_final="2026-06-07",
        empresa_codigo=11495,
    )
    resp = await service.get_payables(filters, "11495")
    assert resp.success
    assert resp.data["resumo"]["emAberto"]["count"] == 1
    client.call_endpoint.assert_awaited_once()
