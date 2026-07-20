from src.services.produto_catalog import ProdutoCatalogService


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
