from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse
from src.services.departmental_fact_pipeline import DepartmentalFactPipeline


class FakePaginator:
    async def collect(self, primary, fallback, params):
        payloads = {
            "produto": [
                {"empresaCodigo": 11495, "produtoCodigo": 10, "grupoCodigo": 24554},
                {"empresaCodigo": 11495, "produtoCodigo": 20, "grupoCodigo": 26039},
            ],
            "venda_item": [
                {
                    "empresaCodigo": 11495,
                    "vendaItemCodigo": 1,
                    "produtoCodigo": 10,
                    "totalVenda": "100",
                    "totalCusto": "70",
                },
                {
                    "empresaCodigo": 11495,
                    "vendaItemCodigo": 2,
                    "produtoCodigo": 20,
                    "totalVenda": "30",
                    "totalCusto": "15",
                },
            ],
            "produto_estoque": [
                {
                    "empresaCodigo": 11495,
                    "estoqueCodigo": 3,
                    "produtoCodigo": 10,
                    "saldoEstoque": "50",
                }
            ],
        }
        return WebPostoResponse.ok(
            {
                "resultados": payloads[primary],
                "pagination": {"complete": True, "pages": 1, "termination": "SHORT_BATCH"},
            }
        )


class FakeClient:
    async def call_endpoint(self, endpoint, params):
        if endpoint == "despesas_financeiro_rede":
            return WebPostoResponse.ok(
                [{"empresaCodigo": 11495, "codigo": 4, "valor": "10"}]
            )
        return WebPostoResponse.ok(
            [{"empresaCodigo": 11495, "caixaCodigo": 5, "apurado": "90"}]
        )


async def test_daily_pipeline_builds_reconciled_batches_and_quarantine():
    result = await DepartmentalFactPipeline(FakeClient(), FakePaginator()).build_day(
        11495, "2026-07-23"
    )

    assert result["materialized"] is True
    assert result["publishable"] is False
    assert "QUARANTINE_ABOVE_TOLERANCE:sales" in result["blockingReasons"]
    assert "QUARANTINE_ABOVE_TOLERANCE:expenses" in result["blockingReasons"]
    assert result["catalogCoverage"] == {"products": 2, "productsWithGroup": 2}
    assert len(result["batches"]["sales"].facts) == 1
    assert len(result["batches"]["sales"].quarantine) == 1
    assert result["batches"]["sales"].reconciliation_difference == 0
    assert result["batches"]["expenses"].quarantine[0].quarantine_reason == "SEM_GRUPO"


async def test_pipeline_can_publish_when_all_nonempty_batches_are_classified():
    class ClassifiedClient:
        async def call_endpoint(self, endpoint, params):
            if endpoint == "despesas_financeiro_rede":
                return WebPostoResponse.ok(
                    [{"empresaCodigo": 11495, "codigo": 4, "grupoCodigo": 24554, "valor": 10}]
                )
            return WebPostoResponse.ok(
                [{"empresaCodigo": 11495, "caixaCodigo": 5, "grupoCodigo": 24554, "apurado": 90}]
            )

    class ClassifiedPaginator(FakePaginator):
        async def collect(self, primary, fallback, params):
            response = await super().collect(primary, fallback, params)
            response.data["resultados"] = [
                {**row, "grupoCodigo": 24554}
                for row in response.data["resultados"]
                if row.get("produtoCodigo") != 20
            ]
            return response

    result = await DepartmentalFactPipeline(
        ClassifiedClient(), ClassifiedPaginator()
    ).build_day(11495, "2026-07-23")

    assert result["materialized"] is True
    assert result["publishable"] is True
    assert result["blockingReasons"] == []


async def test_pipeline_blocks_when_pagination_cannot_prove_completion():
    class BrokenPaginator:
        async def collect(self, primary, fallback, params):
            return WebPostoResponse.fail(
                WebPostoError(endpoint=primary, type="CURSOR_STALLED")
            )

    result = await DepartmentalFactPipeline(FakeClient(), BrokenPaginator()).build_day(
        5555, "2026-07-23"
    )

    assert result["publishable"] is False
    assert "produto:CURSOR_STALLED" in result["blockingReasons"]
    assert result["batches"] == {}


async def test_pipeline_rejects_company_outside_management_scope_without_io():
    result = await DepartmentalFactPipeline(FakeClient(), FakePaginator()).build_day(
        5256, "2026-07-23"
    )

    assert result["publishable"] is False
    assert result["blockingReasons"] == ["UNLICENSED_COMPANY"]
