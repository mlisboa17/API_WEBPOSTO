from unittest.mock import AsyncMock

import pytest

from src.models.response_model import WebPostoResponse
from src.services.network_financial_overview_service import (
    FinancialOverviewFilters,
    NetworkFinancialOverviewService,
)


@pytest.mark.asyncio
async def test_paginated_fetch_stops_when_webposto_repeats_the_same_page() -> None:
    client = AsyncMock()
    client.call_endpoint.return_value = WebPostoResponse.ok(
        [{"movimentoContaCodigo": 1}, {"movimentoContaCodigo": 2}]
    )
    service = NetworkFinancialOverviewService(client)
    filters = FinancialOverviewFilters(data_inicial="2026-07-01", data_final="2026-07-01")

    rows = await service._fetch_paginated_endpoint("movimento_conta", filters)

    assert [row["movimentoContaCodigo"] for row in rows] == [1, 2]
    assert client.call_endpoint.await_count == 2
