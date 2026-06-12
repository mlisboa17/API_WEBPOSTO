"""Testes F07.4 — Produtos Vendidos Performance & Margin Intelligence."""
from __future__ import annotations

import pytest

from src.services.produtos_vendidos_performance_service import ProdutosVendidosPerformanceService


def test_apply_margin_fields():
    svc = ProdutosVendidosPerformanceService()
    items = [
        {
            "vendaItemCodigo": 1,
            "valorTotal": 10.0,
            "quantidade": 2,
            "produtoCodigo": 100,
            "combustivel": False,
        }
    ]
    vi_rows = [{"vendaItemCodigo": 1, "totalCusto": 6.0, "precoCusto": 3.0}]
    out = svc._apply_margin_fields(items, vi_rows)
    assert out[0]["margemBruta"] == 4.0
    assert out[0]["margemBrutaPct"] == 40.0
    assert out[0]["lineageMargem"]


def test_product_sales_performance_ranking():
    svc = ProdutosVendidosPerformanceService()
    pv = [
        {"produtoCodigo": 1, "produtoNome": "A", "quantidade": 5, "valorTotal": 50, "margemBruta": 10},
        {"produtoCodigo": 2, "produtoNome": "B", "quantidade": 1, "valorTotal": 100, "margemBruta": 30},
    ]
    perf = svc._product_sales_performance(pv)
    assert perf["topProdutoReceita"]["produtoCodigo"] == 2
    assert perf["topProdutoVolume"]["produtoCodigo"] == 1


@pytest.mark.asyncio
async def test_build_payload_f074_homologated():
    svc = ProdutosVendidosPerformanceService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F07.4"
    assert "productSalesPerformance" in data
    assert "marginIntelligence" in data
    assert "mixHealthCommercial" in data
    assert "opportunityEngine" in data
    assert data["parecerFinal"].startswith("[PARECER FINAL:")
    assert data["governanceRules"]["proibidoConveniencia"] is True
    assert data["executiveAnswers"].get("14_termoConveniencia") is False
