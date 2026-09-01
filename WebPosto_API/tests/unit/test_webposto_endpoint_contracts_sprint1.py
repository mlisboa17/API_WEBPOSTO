from src.gateway.webposto_endpoint_contracts import WEBPOSTO_ENDPOINT_CONTRACTS


def test_capped_master_and_sales_endpoints_are_marked_as_paginated():
    for endpoint in (
        "produto",
        "produto_empresa",
        "grupo",
        "grupo_meta",
        "venda",
        "venda_item",
        "produto_estoque",
        "estoque_periodo",
    ):
        assert WEBPOSTO_ENDPOINT_CONTRACTS[endpoint].supports_pagination is True
