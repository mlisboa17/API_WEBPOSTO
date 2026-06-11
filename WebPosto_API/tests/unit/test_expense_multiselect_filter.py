"""Testes unitários — filtro multiselect de despesas (P0.2)."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.response_model import WebPostoResponse
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService


def _service_with_rows(rows: list[dict]) -> NetworkFinancialOverviewService:
    client = MagicMock()
    service = NetworkFinancialOverviewService(client)

    async def _call(endpoint_key: str, params=None):
        del params
        if endpoint_key == "despesas_financeiro_rede":
            payload = rows
        else:
            payload = []
        return WebPostoResponse.ok({"resultados": payload, "synthetic": False, "ultimaPagina": True})

    client.call_endpoint = AsyncMock(side_effect=_call)
    return service


@pytest.mark.parametrize(
    ("filters", "row_code", "expected"),
    [
        (FinancialOverviewFilters("2026-06-01", "2026-06-07", empresa_codigo=11495), 11495, True),
        (FinancialOverviewFilters("2026-06-01", "2026-06-07", empresa_codigo=11495), 5555, False),
        (
            FinancialOverviewFilters("2026-06-01", "2026-06-07", empresa_codigos=(11495, 5555)),
            11495,
            True,
        ),
        (
            FinancialOverviewFilters("2026-06-01", "2026-06-07", empresa_codigos=(11495, 5555)),
            5256,
            False,
        ),
        (FinancialOverviewFilters("2026-06-01", "2026-06-07"), 5256, True),
    ],
)
def test_expense_matches_empresa(filters, row_code, expected) -> None:
    service = NetworkFinancialOverviewService(MagicMock())
    row = {"empresaCodigo": row_code, "valor": "10", "data": "2026-06-01", "planoConta": "x"}
    assert service._expense_matches_empresa(row, filters) is expected


@pytest.mark.asyncio
async def test_load_filtered_expenses_multiselect_only_two_filiais() -> None:
    rows = [
        {"empresaCodigo": 11495, "data": "2026-06-01", "valor": 100, "descricaoDocumento": "a"},
        {"empresaCodigo": 5555, "data": "2026-06-01", "valor": 200, "descricaoDocumento": "b"},
        {"empresaCodigo": 5256, "data": "2026-06-01", "valor": 300, "descricaoDocumento": "c"},
    ]
    service = _service_with_rows(rows)
    filters = FinancialOverviewFilters(
        data_inicial="2026-06-01",
        data_final="2026-06-07",
        empresa_codigos=(11495, 5555),
    )
    result, err = await service._load_filtered_expenses(filters)
    assert err is None
    assert len(result) == 2
    codes = {r["empresaCodigo"] for r in result}
    assert codes == {11495, 5555}
    service.client.call_endpoint.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_financial_expenses_single_fetch() -> None:
    rows = [
        {"empresaCodigo": 11495, "data": "2026-06-01", "valor": 50, "descricaoDocumento": "x"},
        {"empresaCodigo": 5256, "data": "2026-06-01", "valor": 99, "descricaoDocumento": "y"},
    ]
    service = _service_with_rows(rows)
    service._resolve_empresas = AsyncMock(
        return_value=([{"empresaCodigo": 11495}], None)
    )
    service._empresa_lookup = MagicMock(return_value={11495: "POSTO VIP"})
    service._empresa_name_by_codigo = MagicMock(return_value="POSTO VIP")

    filters = FinancialOverviewFilters(
        data_inicial="2026-06-01",
        data_final="2026-06-07",
        empresa_codigo=11495,
    )
    resp = await service.get_financial_expenses(filters, page=1, limit=500)
    assert resp.success
    data = resp.data or {}
    assert data["total"] == 1
    assert data["data"][0]["empresaCodigo"] == 11495
    assert Decimal(str(data["data"][0]["valor"])) == Decimal("50")
    assert service.client.call_endpoint.await_count >= 1
    financeiro_calls = [
        c for c in service.client.call_endpoint.await_args_list if c.args[0] == "despesas_financeiro_rede"
    ]
    assert len(financeiro_calls) == 1
