"""Testes F07.1 — Produtos Vendidos catálogo & departamentalização."""
from __future__ import annotations

import pytest

from src.services.non_fuel_product_sales_service import DEPARTMENTS, NonFuelProductSalesService


def test_departments_f071():
    assert "COMBUSTIVEL" in DEPARTMENTS
    assert "PRODUTOS_DE_LOJA" in DEPARTMENTS
    assert "NAO_CLASSIFICADO" in DEPARTMENTS
    assert "CONVENIENCIA" not in DEPARTMENTS


def test_classify_fuel_vs_produtos_vendidos():
    svc = NonFuelProductSalesService()
    dept, _, conf, ev = svc._classify_department(
        1257884, {"nome": "GASOLINA COMUM.", "combustivel": True, "tipoProduto": "C"}, {"bicoCodigo": 42903}
    )
    assert dept == "COMBUSTIVEL"
    assert conf == "ALTA"
    dept2, label2, _, _ = svc._classify_department(
        1803673, {"nome": "Item loja", "combustivel": False, "tipoProduto": "L"}, {}
    )
    assert dept2 == "PRODUTOS_DE_LOJA"
    assert label2 == "Produtos Vendidos"


def test_homologated_items_have_empresa_codigo():
    svc = NonFuelProductSalesService()
    layers = svc._homologated_layers("2026-06-01", "2026-06-07", None)
    catalog = svc._catalog_from_produto_rows(layers["produtoRows"])
    filiais_map = {int(f["empresaCodigo"]): f["nomeFilial"] for f in layers["filiais"]}
    items = svc._build_sale_items(layers, catalog, filiais_map)
    assert items
    assert all(i.get("empresaCodigo") for i in items)
    assert all(i.get("lineage") for i in items)


@pytest.mark.asyncio
async def test_build_full_payload_f071():
    svc = NonFuelProductSalesService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F07.1"
    assert data["fonte"]["segregacaoPorEmpresaCodigo"] is True
    assert "paginationEngine" in data
    assert "productCatalogCompleteness" in data
    assert "produtosVendidosKpiEngine" in data
    qa = data["qa"]
    assert qa["semCombustivelMisturado"] is True
    assert qa["semVendaSemEmpresaCodigo"] is True
    assert data["parecerFinal"].startswith("[PARECER FINAL:")
    assert data["governanceRules"]["proibidoConveniencia"] is True
