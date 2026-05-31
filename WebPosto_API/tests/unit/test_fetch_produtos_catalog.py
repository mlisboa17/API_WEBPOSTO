"""Mapeamento do catálogo de produtos."""

from decimal import Decimal

from src.application.usecases.fetch_produtos_catalog import map_raw_produto, parse_produto_response


def test_map_raw_produto_webposto_fields():
    row = {
        "produtoCodigo": 1257884,
        "nome": "GASOLINA COMUM.",
        "referenciaCodigo": "000004",
        "grupoCodigo": 24554,
        "combustivel": True,
        "precoVenda": 5.89,
        "codigoNcm": "27101259",
        "cstIcms": 60,
    }
    p = map_raw_produto(row)
    assert p.id == 1257884
    assert "GASOLINA" in p.descricao
    assert p.codigo_barra == "000004"
    assert p.codigo_grupo == 24554
    assert p.cst_icms == "060"
    assert p.combustivel is True


def test_parse_produto_response_resultados():
    raw = {"resultados": [{"produtoCodigo": 1, "nome": "ETANOL"}], "total": 1}
    rows, total = parse_produto_response(raw, 1, 50)
    assert len(rows) == 1
    assert total == 1
