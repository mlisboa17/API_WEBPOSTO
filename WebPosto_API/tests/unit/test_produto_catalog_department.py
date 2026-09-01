from src.services.produto_catalog import ProdutoCatalogService


class _FakeClient:
    """Cliente falso que devolve PRODUTO base sem nomes reais para o produto 20."""

    def __init__(self, base_rows: list[dict], empresa_rows: dict[int, list[dict]]):
        self._base_rows = base_rows
        self._empresa_rows = empresa_rows

    async def call_endpoint(self, name, params=None):
        from src.models.response_model import WebPostoResponse

        if name == "produto":
            return WebPostoResponse.ok(self._base_rows)
        if name == "produto_empresa":
            empresa_codigo = (params or {}).get("empresaCodigo")
            return WebPostoResponse.ok(self._empresa_rows.get(empresa_codigo, []))
        raise AssertionError(f"unexpected endpoint {name}")


def test_catalog_preserves_group_code_and_department() -> None:
    row = {
        "produtoCodigo": 1001,
        "nome": "Gasolina comum",
        "grupoCodigo": 24554,
        "nomeGrupo": "COMBUSTIVEIS",
        "tipoProduto": "C",
    }

    product = ProdutoCatalogService._normalize_entry(row, "/INTEGRACAO/PRODUTO")

    assert product is not None
    assert product["grupoCodigo"] == 24554
    assert product["departamento"] == "combustiveis"
    assert product["classificacaoStatus"] == "CONFIRMADA_GRUPO"


def test_catalog_maps_real_store_group_to_convenience() -> None:
    product = ProdutoCatalogService._normalize_entry(
        {"produtoCodigo": 2001, "descricao": "Coxinha", "codigoGrupo": 55444},
        "/INTEGRACAO/PRODUTO",
    )

    assert product is not None
    assert product["departamento"] == "conveniencia"


def test_catalog_does_not_guess_ambiguous_group() -> None:
    product = ProdutoCatalogService._normalize_entry(
        {"produtoCodigo": 3001, "descricao": "Item diverso", "grupoCodigo": 26039},
        "/INTEGRACAO/PRODUTO",
    )

    assert product is not None
    assert product["departamento"] is None
    assert product["classificacaoStatus"] == "NAO_CLASSIFICADA"
    assert product["classificacaoMotivo"] == "GRUPO_AMBIGUO:DIVERSOS"


async def test_get_catalog_resolves_generic_name_via_lmc_cross_reference() -> None:
    ProdutoCatalogService._cache.clear()
    client = _FakeClient(
        base_rows=[
            {"produtoCodigo": 10, "nome": "Diesel S10", "grupoCodigo": 24554, "produtoLmcCodigo": 555},
            {"produtoCodigo": 20, "grupoCodigo": 24554, "produtoLmcCodigo": 555},
        ],
        empresa_rows={},
    )
    service = ProdutoCatalogService(client)

    response = await service.get_catalog([11495])

    assert response.success is True
    products = {p["produtoCodigo"]: p for p in response.data["products"]}
    assert products[20]["nomeProduto"] == "Diesel S10"
    assert "LMC_CROSS_REF" in products[20]["source"]

