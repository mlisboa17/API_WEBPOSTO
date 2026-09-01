import pytest

from unittest.mock import MagicMock

from src.models.response_model import WebPostoResponse
from src.services.director_financial_reconciliation_pipeline import (
    DirectorFinancialReconciliationPipeline,
)


class EmptyReviewStore:
    def get(self, fact_id: str):
        return None

    def get_allocation(self, account_code):
        return None

    def get_rule(self, account_code):
        return None


class FakeClient:
    async def call_endpoint(self, endpoint, params):
        if endpoint == "despesas_financeiro_rede":
            return WebPostoResponse.ok([{
                "empresaCodigo": 11495,
                "codigo": 1,
                "data": "2026-07-01",
                "valor": "100.00",
                "planoContaGerencialCodigo": 42,
                "planoContaGerencialDescricao": "DESPESA COMBUSTIVEIS",
                "descricaoDocumento": "NF 10",
            }, {
                "empresaCodigo": 5333,
                "codigo": 2,
                "data": "2026-07-01",
                "valor": "999.00",
            }])
        if endpoint == "financeiro":
            return WebPostoResponse.ok([{
                "empresaCodigo": 11495,
                "tituloPagarCodigo": 9,
                "dataMovimento": "2026-07-01",
                "valor": "100.00",
                "planoContaGerencialCodigo": 42,
                "numeroTitulo": "NF 10",
                "situacao": "Pago",
            }])
        return WebPostoResponse.ok([])


class CompleteCoverage:
    async def collect_account_movements(self, start, end, companies):
        return WebPostoResponse.ok({
            "resultados": [],
            "coverage": {"complete": True, "strategy": "COMPANY_DAY_CURSOR"},
        })


async def test_pipeline_releases_only_confirmed_expense_by_company_and_department() -> None:
    pipeline = DirectorFinancialReconciliationPipeline(FakeClient(), CompleteCoverage())
    result = await pipeline.build("2026-07-01", "2026-07-01", 11495)

    assert result["complete"] is True
    assert result["publication"]["dreTotalsReleased"] is True
    assert result["publication"]["rawPayloadExposed"] is False
    assert result["departmentGovernance"]["eligible"] == 1
    assert result["treasury"]["requiresDepartment"] is False
    assert len(result["departmentalDre"]) == 3
    assert len(result["executiveSummary"]) == 3
    combustible = next(
        row for row in result["executiveSummary"] if row["department"] == "combustiveis"
    )
    assert combustible == {
        "companyCode": 11495,
        "companyName": "POSTO VIP",
        "department": "combustiveis",
        "confirmedDreAmount": "100.00",
        "confirmedMatches": 1,
        "probableMatches": 0,
        "quarantined": 0,
        "unmatched": 0,
        "duplicates": 0,
    }
    assert {row["department"] for row in result["executiveSummary"]} == {
        "combustiveis", "conveniencia", "lubrificantes"
    }


async def test_pipeline_blocks_publication_when_movement_coverage_fails() -> None:
    class FailedCoverage:
        async def collect_account_movements(self, start, end, companies):
            from src.models.error_model import WebPostoError
            return WebPostoResponse.fail(WebPostoError(type="CURSOR_STALLED"))

    result = await DirectorFinancialReconciliationPipeline(FakeClient(), FailedCoverage()).build(
        "2026-07-01", "2026-07-01", 11495
    )
    assert result["complete"] is False
    assert result["publication"]["dreTotalsReleased"] is False
    assert result["warnings"]


async def test_pipeline_rejects_company_outside_scope() -> None:
    with pytest.raises(ValueError, match="fora das tres licencas"):
        await DirectorFinancialReconciliationPipeline(FakeClient(), CompleteCoverage()).build(
            "2026-07-01", "2026-07-01", 5333
        )


async def test_review_queue_exposes_webposto_evidence() -> None:
    class UnclassifiedClient(FakeClient):
        async def call_endpoint(self, endpoint, params):
            if endpoint == "despesas_financeiro_rede":
                return WebPostoResponse.ok([{
                    "empresaCodigo": 11495,
                    "codigo": 80,
                    "data": "2026-07-01",
                    "valor": "80.00",
                    "planoConta": "pagamento pudim",
                    "planoContaCodigo": 29019,
                    "categoriaLogosV3": "COMPRAS",
                }])
            return WebPostoResponse.ok([])

    result = await DirectorFinancialReconciliationPipeline(
        UnclassifiedClient(), CompleteCoverage(), review_store=EmptyReviewStore()
    ).build("2026-07-01", "2026-07-01", 11495)

    fact = result["reviewableFacts"][0]
    assert fact["companyName"] == "POSTO VIP"
    assert fact["description"] == "pagamento pudim"
    assert fact["managementAccountCode"] == "29019"
    assert fact["managementCategory"] == "COMPRAS"
    assert result["publication"]["dreTotalsReleased"] is False
