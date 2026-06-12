"""Testes F07.3 — Product Master Optimization."""
from __future__ import annotations

import pytest

from src.domain.adelaide.fuel_catalog import eh_combustivel_codigo
from src.services.product_master_cache import ProductMasterCache
from src.services.product_master_optimization_service import (
    RESIDUAL_SKU,
    ProductMasterOptimizationService,
)


def test_residual_sku_is_fuel_catalog():
    assert eh_combustivel_codigo(str(RESIDUAL_SKU))
    assert RESIDUAL_SKU == 1975728


def test_cache_put_get():
    cache = ProductMasterCache()
    cache.clear()
    cache.put(123, 11495, nome_produto="Teste", departamento="PRODUTOS_DE_LOJA", fonte="TEST")
    entry = cache.get(123, 11495)
    assert entry is not None
    assert entry["nomeProduto"] == "Teste"
    assert cache.stats()["cacheHits"] >= 1


def test_fuel_catalog_recovery():
    svc = ProductMasterOptimizationService()
    master: dict = {}
    recovered = svc._apply_fuel_catalog_recovery(
        master, {RESIDUAL_SKU}, {RESIDUAL_SKU: 11495}, {11495: "POSTO VIP"}
    )
    assert recovered == 1
    assert master[RESIDUAL_SKU]["departamento"] == "COMBUSTIVEL"
    assert "Etanol" in master[RESIDUAL_SKU]["nome"]


@pytest.mark.asyncio
async def test_build_payload_f073_homologated():
    svc = ProductMasterOptimizationService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F07.3"
    assert "residualSkuForensics" in data
    assert "productPerformanceBenchmark" in data
    assert data["parecerFinal"].startswith("[PARECER FINAL:")
    assert data["governanceRules"]["proibidoConveniencia"] is True
