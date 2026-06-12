"""Testes F06.4 — Fiscal Reconciliation Hub."""
from __future__ import annotations

import pytest

from src.services.fiscal_reconciliation_hub_service import (
    RISK_LEVELS,
    FiscalReconciliationHubService,
)


def test_risk_levels_complete():
    assert len(RISK_LEVELS) == 4


def test_d01_layers_has_joins():
    svc = FiscalReconciliationHubService()
    d01 = svc._d01_layers()
    assert d01.get("join_nfce_venda")
    assert d01.get("join_abast_vitem")


def test_lineage_engine_has_items():
    svc = FiscalReconciliationHubService()
    d01 = svc._d01_layers()
    lineage = svc._fiscal_lineage_engine({}, {}, {}, d01)
    assert lineage.get("items")
    for item in lineage["items"]:
        assert item.get("lineage")


@pytest.mark.asyncio
async def test_build_full_payload():
    svc = FiscalReconciliationHubService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F06.4"
    assert data["fonte"]["webPostoLive"] is False
    assert data["fonte"]["sped"] is False
    qa = data["qa"]
    assert qa["fonteWebPostoLive"] is False
    assert qa["semCrossTenant"] is True
    assert qa["semProdutoNcmInventado"] is True
    assert qa["motorAuditavel"] is True
    assert qa["lineageCompleto"] is True
    ex = data["executiveAnswers"]
    assert "1_vendasConciliadasNfce" in ex
    assert "20_aprovadoF065" in ex
    assert data["fiscalLineageEngine"]
    assert data["nfceVendaReconciliation"]
    assert data["productSalesReconciliation"]
    assert data["lmcSalesReconciliation"]
    assert data["fiscalFinancialBridge"]
    assert data["fiscalRiskConsolidation"]
    assert data["parecerFinal"].startswith("[PARECER FINAL:")
