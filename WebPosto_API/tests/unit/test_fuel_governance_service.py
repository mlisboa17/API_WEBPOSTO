"""Testes F06.5 — Fuel Governance."""
from __future__ import annotations

import pytest

from src.services.fuel_governance_service import (
    COMPLIANCE_LEVELS,
    DISCIPLINE_LEVELS,
    FuelGovernanceService,
)


def test_compliance_and_discipline_levels():
    assert len(COMPLIANCE_LEVELS) == 3
    assert len(DISCIPLINE_LEVELS) == 4


def test_lmc_records_have_lineage():
    svc = FuelGovernanceService()
    records = svc._extract_lmc_records("2026-06-01", "2026-06-07")
    assert records
    for row in records:
        assert row.get("lineage")
        assert row.get("homologado")


def test_compliance_no_invented_fraud():
    svc = FuelGovernanceService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    compliance = svc._lmc_compliance_audit(layers)
    intel = svc._fuel_governance_intelligence(
        layers,
        compliance,
        svc._routine_adherence_audit(layers, compliance),
        svc._operational_discipline_audit(layers, compliance),
    )
    assert intel["semFraudePresumida"] is True
    assert intel["semPerdaPresumida"] is True


@pytest.mark.asyncio
async def test_build_full_payload():
    svc = FuelGovernanceService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F06.5"
    assert data["fonte"]["readOnly"] is True
    assert data["fonte"]["semFraudePresumida"] is True
    qa = data["qa"]
    assert qa["semFraudePresumida"] is True
    assert qa["semPerdasPresumidas"] is True
    assert qa["semScoreExecutivoNovo"] is True
    assert qa["semIaAutonoma"] is True
    assert qa["motorAuditavel"] is True
    assert data["lmcComplianceAudit"]
    assert data["parecerFinal"].startswith("[PARECER FINAL:")
