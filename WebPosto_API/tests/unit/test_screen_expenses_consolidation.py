"""Testes unitários — listagem consolidada da tela de despesas (P0)."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.response_model import WebPostoResponse
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService


def _service_with_sources(
    financeiro: list[dict],
    caixa_rede: list[dict] | None = None,
    caixa: list[dict] | None = None,
    apresentado: list[dict] | None = None,
    apresentado_rede: list[dict] | None = None,
) -> NetworkFinancialOverviewService:
    client = MagicMock()
    service = NetworkFinancialOverviewService(client)

    async def _call(endpoint_key: str, params=None):
        del params
        mapping = {
            "despesas_financeiro_rede": financeiro,
            "caixa_rede": caixa_rede or [],
            "caixa": caixa or [],
            "caixa_apresentado": apresentado or [],
            "caixa_apresentado_rede": apresentado_rede or [],
        }
        rows = mapping.get(endpoint_key, [])
        return WebPostoResponse.ok({"resultados": rows, "synthetic": False, "ultimaPagina": True})

    client.call_endpoint = AsyncMock(side_effect=_call)
    return service


@pytest.mark.asyncio
async def test_load_screen_expenses_merges_financeiro_caixa_pdv() -> None:
    service = _service_with_sources(
        financeiro=[
            {
                "empresaCodigo": 5555,
                "data": "2026-06-08",
                "valor": 135,
                "descricaoDocumento": "BOBINA TERMICA",
            }
        ],
        apresentado=[
            {
                "empresaCodigo": 5555,
                "caixaCodigo": 1,
                "pdvCodigo": 15880,
                "funcionarioCodigo": 158924,
                "dataMovimento": "2026-06-08",
                "despesaApresentado": 59.0,
                "despesaApurado": 59.0,
            }
        ],
        caixa_rede=[
            {
                "empresaCodigo": 5555,
                "caixaCodigo": 1,
                "pdvCodigo": 15880,
                "funcionarioCodigo": 158924,
                "dataMovimento": "2026-06-08",
            }
        ],
    )
    filters = FinancialOverviewFilters(
        data_inicial="2026-06-08",
        data_final="2026-06-08",
        empresa_codigo=5555,
    )
    rows, err = await service._load_screen_expenses(filters)
    assert err is None
    assert len(rows) == 2
    origens = {row["origem"] for row in rows}
    assert origens == {"financeiro", "caixa"}
    assert len([r for r in rows if r.get("origem") == "caixa"]) == 1


@pytest.mark.asyncio
async def test_load_screen_expenses_origem_filter_financeiro_only() -> None:
    service = _service_with_sources(
        financeiro=[{"empresaCodigo": 5555, "data": "2026-06-08", "valor": 10, "descricaoDocumento": "A"}],
        caixa_rede=[{"empresaCodigo": 5555, "caixaCodigo": 2, "dataMovimento": "2026-06-08"}],
        apresentado=[{"empresaCodigo": 5555, "caixaCodigo": 2, "dataMovimento": "2026-06-08", "despesaApurado": 20}],
    )
    filters = FinancialOverviewFilters(
        data_inicial="2026-06-08",
        data_final="2026-06-08",
        empresa_codigo=5555,
        origem="financeiro",
    )
    rows, _ = await service._load_screen_expenses(filters)
    assert len(rows) == 1
    assert rows[0]["origem"] == "financeiro"


@pytest.mark.asyncio
async def test_get_financial_expenses_uses_screen_loader() -> None:
    service = _service_with_sources(
        financeiro=[{"empresaCodigo": 5555, "data": "2026-06-08", "valor": 135, "descricaoDocumento": "BOBINA TERMICA"}],
        caixa_rede=[{"empresaCodigo": 5555, "caixaCodigo": 9, "pdvCodigo": 1, "dataMovimento": "2026-06-08"}],
        apresentado=[{"empresaCodigo": 5555, "caixaCodigo": 9, "despesaApurado": 59, "dataMovimento": "2026-06-08"}],
    )
    service._resolve_empresas = AsyncMock(return_value=([{"empresaCodigo": 5555, "fantasia": "AP CASA CAIADA"}], None))
    service._empresa_lookup = MagicMock(return_value={5555: "AP CASA CAIADA"})
    service._empresa_name_by_codigo = MagicMock(return_value="AP CASA CAIADA")

    resp = await service.get_financial_expenses(
        FinancialOverviewFilters(data_inicial="2026-06-08", data_final="2026-06-08", empresa_codigo=5555),
        page=1,
        limit=500,
    )
    assert resp.success
    data = resp.data or {}
    assert data["total"] == 2
    assert "resumoPorOrigem" in data
    assert Decimal(str(data["resumoPorOrigem"]["financeiro"]["valor"])) == Decimal("135")
    assert data["resumoPorOrigem"]["caixa"]["count"] == 1
