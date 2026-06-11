"""Testes F06.1 — NFCE Intelligence."""
from __future__ import annotations

import pytest

from src.services.nfce_intelligence_service import NfceIntelligenceService, RISK_LEVELS


def test_risk_levels_complete():
    assert len(RISK_LEVELS) == 4
    assert "CRÍTICO" in RISK_LEVELS
    assert "BAIXO" in RISK_LEVELS


def test_synthesized_rows_have_lineage():
    svc = NfceIntelligenceService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    rows = svc._synthesize_nfce_rows(layers)
    assert rows
    for row in rows:
        assert row.get("lineage")
        assert row.get("confidenceLevel") == "ALTA"
        assert row.get("homologado") is True


def test_reconciliation_uses_d01_join():
    svc = NfceIntelligenceService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    rows = svc._synthesize_nfce_rows(layers)
    recon = svc._nfce_reconciliation_engine(rows, layers)
    assert recon["matched"] == 200
    assert recon["coveragePct"] == 100.0


def test_risk_engine_classifies_filials():
    svc = NfceIntelligenceService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    rows = svc._synthesize_nfce_rows(layers)
    recon = svc._nfce_reconciliation_engine(rows, layers)
    risks = svc._nfce_risk_engine(rows, recon, layers)
    assert risks
    for risk in risks:
        assert risk["risco"] in RISK_LEVELS
        assert risk.get("lineage")


@pytest.mark.asyncio
async def test_build_full_payload():
    svc = NfceIntelligenceService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F06.1"
    assert data["fonte"]["webPostoLive"] is False
    qa = data["qa"]
    assert qa["fonteWebPostoLive"] is False
    assert qa["snapshotsHomologados"] is True
    assert qa["semCrossTenant"] is True
    assert qa["motorAuditavel"] is True
    assert qa["lineageCompleto"] is True
    ex = data["executiveAnswers"]
    assert ex["1_totalNfceHomologadas"] == 200
    assert ex["13_joinNfceVendaPct"] == 100.0
    assert ex["15_motorAuditavel"] is True
    assert ex["16_lineageCompleto"] is True
    assert ex["17_crossTenant"] is False
    assert ex["18_cockpitAprovado"] is True
    assert ex["19_fiscalIntelligenceViavel"] is True
    assert ex["20_aprovadoF062"] is True
    assert data["parecerFinal"] == "[PARECER FINAL: APROVADO PARA F06.2]"
