from src.models.response_model import WebPostoResponse
from src.services.financial_partition_coverage_service import FinancialPartitionCoverageService


class FakeMovementClient:
    def __init__(self):
        self.calls = []

    async def call_endpoint(self, key, params):
        self.calls.append(dict(params))
        company = params["empresaCodigo"]
        cursor = params.get("ultimoCodigo")
        if cursor is None:
            return WebPostoResponse.ok([
                {"movimentoContaCodigo": company * 10 + 1, "empresaCodigo": company},
                {"movimentoContaCodigo": company * 10 + 2, "empresaCodigo": company},
            ])
        return WebPostoResponse.ok([])


async def test_collects_each_licensed_company_and_day_with_cursor() -> None:
    client = FakeMovementClient()
    service = FinancialPartitionCoverageService(client)
    response = await service.collect_account_movements(
        "2026-07-01", "2026-07-02", (11495, 5555, 74014)
    )

    assert response.success is True
    assert response.data["coverage"]["complete"] is True
    assert len(response.data["coverage"]["partitions"]) == 6
    assert response.data["coverage"]["records"] == 6


async def test_rejects_company_outside_license_scope() -> None:
    response = await FinancialPartitionCoverageService(FakeMovementClient()).collect_account_movements(
        "2026-07-01", "2026-07-01", (5333,)
    )
    assert response.success is False
    assert response.error.type == "COMPANY_OUT_OF_SCOPE"


async def test_rejects_foreign_company_inside_partition() -> None:
    class LeakyClient:
        async def call_endpoint(self, key, params):
            return WebPostoResponse.ok([{"movimentoContaCodigo": 1, "empresaCodigo": 5333}])

    response = await FinancialPartitionCoverageService(LeakyClient()).collect_account_movements(
        "2026-07-01", "2026-07-01", (11495,)
    )
    assert response.success is False
    assert response.error.type == "TENANT_SCOPE_VIOLATION"
