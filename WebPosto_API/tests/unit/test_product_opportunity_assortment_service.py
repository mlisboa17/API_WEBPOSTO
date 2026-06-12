"""Testes F07.5 — Product Opportunity & Assortment Intelligence."""
from __future__ import annotations

import pytest

from src.services.product_opportunity_assortment_service import ProductOpportunityAssortmentService


def _sample_pv() -> list[dict]:
    return [
        {
            "produtoCodigo": 1,
            "produtoNome": "Prod A",
            "departamento": "PRODUTOS_DE_LOJA",
            "quantidade": 10,
            "valorTotal": 100,
            "margemBruta": 40,
            "margemBrutaPct": 40,
            "empresaCodigo": 11495,
        },
        {
            "produtoCodigo": 2,
            "produtoNome": "Prod B",
            "departamento": "PRODUTOS_DE_LOJA",
            "quantidade": 10,
            "valorTotal": 80,
            "margemBruta": 8,
            "margemBrutaPct": 10,
            "empresaCodigo": 11495,
        },
        {
            "produtoCodigo": 3,
            "produtoNome": "Prod C",
            "departamento": "LUBRIFICANTES",
            "quantidade": 2,
            "valorTotal": 50,
            "margemBruta": 25,
            "margemBrutaPct": 50,
            "empresaCodigo": 5555,
        },
    ]


def test_margin_leaders():
    svc = ProductOpportunityAssortmentService()
    rollup = svc._product_rollup(_sample_pv())
    leaders = svc._margin_leaders(rollup)
    assert leaders["topProdutoMargemPct"]["produtoCodigo"] == 3


def test_high_volume_low_margin():
    svc = ProductOpportunityAssortmentService()
    rollup = svc._product_rollup(_sample_pv())
    low = svc._high_volume_low_margin(rollup, 30)
    codes = {p["produtoCodigo"] for p in low["produtos"]}
    assert 2 in codes


def test_commercial_focus():
    svc = ProductOpportunityAssortmentService()
    rollup = svc._product_rollup(_sample_pv())
    leaders = svc._margin_leaders(rollup)
    low = svc._high_volume_low_margin(rollup, 30)
    branch_mix = {
        "filiais": [
            {"empresaCodigo": 11495, "mixProdutosVendidosPct": 30},
            {"empresaCodigo": 5555, "mixProdutosVendidosPct": 25},
        ]
    }
    exp = svc._expansion_potential(rollup, branch_mix, 30)
    focus = svc._commercial_focus_engine(rollup, leaders, low, exp)
    assert focus["totalFoco"] >= 1


@pytest.mark.asyncio
async def test_build_payload_f075_homologated():
    svc = ProductOpportunityAssortmentService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F07.5"
    assert "productOpportunityAssortment" in data
    assert data["parecerFinal"].startswith("[PARECER FINAL:")
    assert data["executiveAnswers"].get("14_termoConveniencia") is False
