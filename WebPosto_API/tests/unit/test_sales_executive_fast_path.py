import pytest

from src.models.response_model import WebPostoResponse
from src.services.network_financial_overview_service import (
    FinancialOverviewFilters,
    NetworkFinancialOverviewService,
)


class Client:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def call_endpoint(self, endpoint, params=None):
        self.calls.append(endpoint)
        if endpoint == "venda":
            return WebPostoResponse.ok([{
                "empresaCodigo": 74014,
                "vendaCodigo": 1,
                "data": "2026-07-01",
                "totalVenda": "123.45",
            }])
        raise AssertionError(f"endpoint detalhado não deveria ser chamado: {endpoint}")


@pytest.mark.asyncio
async def test_sales_totals_skip_heavy_item_and_payment_pagination() -> None:
    client = Client()
    service = NetworkFinancialOverviewService(client)
    filters = FinancialOverviewFilters(
        data_inicial="2026-07-01", data_final="2026-07-01", empresa_codigo=74014
    )

    response = await service._fetch_vendas_produtos(filters, 74014)

    assert response.success is True
    assert response.data["detailCoverage"] == "SALES_TOTALS_ONLY"
    assert client.calls == ["venda"]
