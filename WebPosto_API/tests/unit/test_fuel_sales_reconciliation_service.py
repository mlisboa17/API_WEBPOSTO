from src.models.response_model import WebPostoResponse
from src.services.fuel_sales_reconciliation_service import FuelSalesReconciliationService


class FakeCatalog:
    async def get_catalog(self, _codes):
        return WebPostoResponse.ok(
            {
                "products": [
                    {
                        "produtoCodigo": 10,
                        "nomeProduto": "Gasolina comum",
                        "grupoCodigo": 24554,
                    }
                ]
            }
        )


class FakePaginator:
    async def collect(self, _primary, _fallback, params):
        company = params["empresaCodigo"]
        return WebPostoResponse.ok(
            {
                "resultados": [
                    {
                        "codigo": company * 10,
                        "empresaCodigo": company,
                        "vendaCodigo": company * 100,
                        "vendaItemCodigo": company * 1000,
                        "produtoCodigo": 10,
                        "dataMovimento": "2026-07-01",
                        "quantidade": "10",
                        "precoVenda": "6.00",
                        "precoCusto": "5.00",
                        "totalVenda": "60.00",
                        "totalCusto": "50.00",
                    }
                ],
                "pagination": {"complete": True, "pages": 1, "termination": "SHORT_BATCH"},
            }
        )


async def test_builds_separate_company_results_without_generic_total() -> None:
    service = FuelSalesReconciliationService(
        object(), catalog=FakeCatalog(), paginator=FakePaginator()
    )

    response = await service.build("2026-07-01", "2026-07-01")

    assert response.success is True
    assert response.data["consolidacaoGenerica"] is False
    assert [row["empresaCodigo"] for row in response.data["empresas"]] == [11495, 5555, 74014]
    for company in response.data["empresas"]:
        product = company["produtos"][0]
        assert product["faturamento"] == "60.00"
        assert product["custoRegistrado"] == "50.00"
        assert product["margemRegistrada"] == "10.00"


async def test_filters_single_licensed_company() -> None:
    service = FuelSalesReconciliationService(
        object(), catalog=FakeCatalog(), paginator=FakePaginator()
    )

    response = await service.build("2026-07-01", "2026-07-01", 74014)

    assert response.success is True
    assert len(response.data["empresas"]) == 1
    assert response.data["empresas"][0]["empresaNome"] == "POSTO DOZE FILIAL II"


async def test_rejects_unlicensed_company() -> None:
    service = FuelSalesReconciliationService(
        object(), catalog=FakeCatalog(), paginator=FakePaginator()
    )

    response = await service.build("2026-07-01", "2026-07-01", 5333)

    assert response.success is False
    assert response.error is not None
    assert response.error.status == 403
