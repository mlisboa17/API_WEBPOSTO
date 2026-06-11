"""Testes unitários — dedup fechamento caixa (P0.1-B)."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.response_model import WebPostoResponse
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService


def _service_with_sources(
    financeiro: list[dict],
    caixa_rede: list[dict] | None = None,
    apresentado: list[dict] | None = None,
) -> NetworkFinancialOverviewService:
    client = MagicMock()
    service = NetworkFinancialOverviewService(client)

    async def _call(endpoint_key: str, params=None):
        del params
        mapping = {
            "despesas_financeiro_rede": financeiro,
            "caixa_rede": caixa_rede or [],
            "caixa": [],
            "caixa_apresentado": apresentado or [],
            "caixa_apresentado_rede": [],
        }
        rows = mapping.get(endpoint_key, [])
        return WebPostoResponse.ok({"resultados": rows, "synthetic": False, "ultimaPagina": True})

    client.call_endpoint = AsyncMock(side_effect=_call)
    return service


@pytest.mark.asyncio
async def test_closure_emits_single_line_not_caixa_and_pdv() -> None:
    service = _service_with_sources(
        financeiro=[],
        caixa_rede=[
            {
                "empresaCodigo": 5555,
                "caixaCodigo": 4343023,
                "pdvCodigo": 15880,
                "funcionarioCodigo": 158924,
                "turnoCodigo": 1,
                "dataMovimento": "2026-06-08",
            }
        ],
        apresentado=[
            {
                "empresaCodigo": 5555,
                "caixaCodigo": 4343023,
                "despesaApresentado": 135.0,
                "despesaApurado": 135.0,
                "despesaDiferenca": 0.0,
                "dataMovimento": "2026-06-08",
            }
        ],
    )
    filters = FinancialOverviewFilters(data_inicial="2026-06-08", data_final="2026-06-08", empresa_codigo=5555)
    rows, err = await service._load_screen_expenses(filters)
    assert err is None
    operational = [r for r in rows if r.get("origem") == "caixa"]
    assert len(operational) == 1
    assert operational[0]["caixaCodigo"] == 4343023
    assert Decimal(operational[0]["valor"]) == Decimal("135")
    assert Decimal(operational[0]["despesaApurado"]) == Decimal("135")
    assert Decimal(operational[0]["despesaApresentado"]) == Decimal("135")


@pytest.mark.asyncio
async def test_duplicate_pagination_rows_deduped_by_closure_key() -> None:
    duplicate_row = {
        "empresaCodigo": 5555,
        "caixaCodigo": 4343023,
        "pdvCodigo": 15880,
        "turnoCodigo": 1,
        "dataMovimento": "2026-06-08",
    }
    service = _service_with_sources(
        financeiro=[],
        caixa_rede=[duplicate_row, dict(duplicate_row)],
        apresentado=[
            {
                "empresaCodigo": 5555,
                "caixaCodigo": 4343023,
                "despesaApresentado": 135.0,
                "despesaApurado": 135.0,
                "dataMovimento": "2026-06-08",
            }
        ],
    )
    filters = FinancialOverviewFilters(data_inicial="2026-06-08", data_final="2026-06-08", empresa_codigo=5555)
    rows, _ = await service._load_screen_expenses(filters)
    assert len([r for r in rows if r.get("origem") == "caixa"]) == 1
