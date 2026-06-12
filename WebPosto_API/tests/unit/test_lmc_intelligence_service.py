"""Testes F06.2 — LMC Intelligence."""
from __future__ import annotations

import pytest

from src.services.lmc_intelligence_service import LOSS_BANDS, LmcIntelligenceService


def test_loss_bands_complete():
    assert len(LOSS_BANDS) == 4
    assert "CRÍTICA" in LOSS_BANDS
    assert "BAIXA" in LOSS_BANDS


def test_lmc_records_have_lineage():
    svc = LmcIntelligenceService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    for row in layers["lmc_records"]:
        assert row.get("lineage")
        assert row.get("confidenceLevel") == "ALTA"
        assert row.get("homologado") is True


def test_pump_endpoint_blocked_without_inventing():
    svc = LmcIntelligenceService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    pumps = svc._pump_intelligence(layers)
    assert pumps["classificacaoEndpointDedicado"] == "NÃO DISPONÍVEL"
    for bico in pumps.get("bicosCriticos") or []:
        assert bico.get("fonte") == "LMC_REDE_NESTED"


def test_reconciliation_has_lineage():
    svc = LmcIntelligenceService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    catalog = svc._lmc_catalog_engine(layers)
    recon = svc._fuel_reconciliation_engine(layers, catalog)
    assert recon.get("lineage")
    assert recon.get("abastecimentoTotal") == 200


@pytest.mark.asyncio
async def test_build_full_payload():
    svc = LmcIntelligenceService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F06.2"
    assert data["fonte"]["webPostoLive"] is False
    qa = data["qa"]
    assert qa["fonteWebPostoLive"] is False
    assert qa["snapshotsHomologados"] is True
    assert qa["semCrossTenant"] is True
    assert qa["semCalculoSemOrigem"] is True
    assert qa["semPerdaSemEvidencia"] is True
    assert qa["semReconciliacaoSemLineage"] is True
    assert qa["motorAuditavel"] is True
    assert qa["lineageCompleto"] is True
    ex = data["executiveAnswers"]
    assert ex["2_totalVendido"] > 0
    assert ex["endpointBicoDedicado"] == "NÃO DISPONÍVEL"
    assert ex["16_motorAuditavel"] is True
    assert ex["17_lineageCompleto"] is True
    assert ex["18_crossTenant"] is False
    assert ex["19_lmcIntelligenceViavel"] is True
    assert ex["20_aprovadoF063"] is True
    assert data["parecerFinal"] == "[PARECER FINAL: APROVADO PARA F06.3]"
