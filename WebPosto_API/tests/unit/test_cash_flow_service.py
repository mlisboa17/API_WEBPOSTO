"""Testes F01.2 — Fluxo de Caixa Corporativo."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.response_model import WebPostoResponse
from src.services.corporate_cash_flow_service import (
    ALLOWED_SOURCES,
    FORBIDDEN_SOURCES,
    CorporateCashFlowService,
    _aging_band,
)
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService


def test_aging_bands() -> None:
    ref = date(2026, 6, 7)
    assert _aging_band(date(2026, 6, 1), ref) == "vencido"
    assert _aging_band(date(2026, 6, 7), ref) == "hoje"
    assert _aging_band(date(2026, 6, 10), ref) == "7d"
    assert _aging_band(date(2026, 8, 1), ref) == "acima30"


def test_allowed_forbidden_sources() -> None:
    assert "TITULO_PAGAR" in ALLOWED_SOURCES
    assert "DESPESAS_REDE" in FORBIDDEN_SOURCES


@pytest.mark.asyncio
async def test_build_cash_flow_from_titles_only() -> None:
    fc = CorporateFinanceCenterService(MagicMock())
    fc._fetch_titulo_pagar_all = AsyncMock(
        return_value=(
            [
                {"situacao": "Aberto", "valor": 100, "vencimento": "2026-06-05", "empresaCodigo": 11495},
                {"situacao": "Pago", "valor": 50, "vencimento": "2026-06-03", "dataPagamento": "2026-06-03"},
            ],
            1.0,
        )
    )
    fc._fetch_titulo_receber_all = AsyncMock(
        return_value=(
            [{"pendente": True, "valor": 30, "dataVencimento": "2026-06-06", "empresaCodigo": 11495}],
            1.0,
        )
    )
    fc._fetch_movimento_conta_all = AsyncMock(return_value=([], 1.0))
    fc._fetch_caixa_all = AsyncMock(return_value=([], [], 1.0))
    fc._classify_bank_movements = MagicMock(
        return_value={
            "creditos": {"count": 0, "valor": "0", "items": []},
            "debitos": {"count": 0, "valor": "0", "items": []},
            "tarifas": {"count": 0, "valor": "0", "items": []},
            "transferencias": {"count": 0, "valor": "0", "items": []},
        }
    )

    service = CorporateCashFlowService(fc)
    filters = FinancialOverviewFilters(data_inicial="2026-06-01", data_final="2026-06-07", empresa_codigo=11495)
    resp = await service.build(filters, "11495")
    assert resp.success
    data = resp.data
    assert "DESPESAS_REDE" not in data["sources"]
    assert Decimal(data["cards"]["entradasPrevistas"]) == Decimal("30.00")
    assert Decimal(data["cards"]["saidasPrevistas"]) == Decimal("100.00")
    assert len(data["daily"]) == 7
    assert data["payablesAging"]["vencido"]["count"] == 1
