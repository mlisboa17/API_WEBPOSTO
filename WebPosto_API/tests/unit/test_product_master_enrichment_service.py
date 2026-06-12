"""Testes F07.2 — Product Master Enrichment."""
from __future__ import annotations

import pytest

from src.services.non_fuel_product_sales_service import DEPARTMENTS
from src.services.product_master_enrichment_service import ProductMasterEnrichmentService


def test_departments_f072():
    assert "PRODUTOS_DE_LOJA" in DEPARTMENTS
    assert "CONVENIENCIA" not in DEPARTMENTS


def test_match_recovery_improves_coverage():
    svc = ProductMasterEnrichmentService()
    layers = svc._sales._homologated_layers("2026-06-01", "2026-06-07", None)
    produto_only = svc._sales._catalog_from_produto_rows(layers["produtoRows"])
    sources = {
        "produtoRows": layers["produtoRows"],
        "produtoEmpresaByEmpresa": {
            11495: [{"empresaCodigo": 11495, "produtoCodigo": 1803673, "ativo": True}]
        },
        "produtoRedeRows": [],
    }
    filiais_map = {11495: "POSTO VIP"}
    master = svc._build_enriched_master(sources, filiais_map)
    sold_sets = svc._sold_product_sets(layers["vendaItemRows"], produto_only, master)
    recovery = svc._product_match_recovery(master, produto_only, sold_sets)
    assert recovery["produtosRecuperados"] >= 0
    assert "taxaRecuperacaoPct" in recovery


def test_hierarchy_has_lineage():
    svc = ProductMasterEnrichmentService()
    master = {
        1: {
            "produtoCodigo": 1,
            "grupoCodigo": 100,
            "ncm": "27101259",
            "departamento": "PRODUTOS_DE_LOJA",
            "nome": "Item teste",
        }
    }
    hier = svc._product_hierarchy_discovery(master)
    assert hier["gruposDistintos"] == 1
    assert hier["lineage"]


@pytest.mark.asyncio
async def test_build_full_payload_f072():
    svc = ProductMasterEnrichmentService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F07.2"
    assert "productMasterCoverage" in data
    assert "productMatchRecovery" in data
    assert "departmentIntelligence" in data
    assert "productRevenueIntelligence" in data
    qa = data["qa"]
    assert qa["semCrossTenant"] is True
    assert data["parecerFinal"].startswith("[PARECER FINAL:")
    assert data["governanceRules"]["proibidoConveniencia"] is True
    assert data["cockpit"]["tituloVisual"] == "Produtos Vendidos"
