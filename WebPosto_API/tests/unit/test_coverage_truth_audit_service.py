"""Testes D04.1 — Coverage Truth Audit."""
from __future__ import annotations

import pytest

from src.services.coverage_truth_audit_service import AUTHORIZED_FILIAIS, CoverageTruthAuditService


@pytest.fixture
def svc() -> CoverageTruthAuditService:
    return CoverageTruthAuditService()


def test_authorized_filiais():
    assert 11495 in AUTHORIZED_FILIAIS
    assert 5555 in AUTHORIZED_FILIAIS


def test_rejects_unauthorized_filial(svc: CoverageTruthAuditService):
    import asyncio

    resp = asyncio.run(svc.build("2026-06-01", "2026-06-07", 9999))
    assert not resp.success


def test_trust_challenge_finds_gap(svc: CoverageTruthAuditService):
    layers = svc._load_layers()
    assert layers["d04_ex"]
    business = svc._business_coverage(layers)
    people = svc._people_challenge(layers, layers["d04_ex"])
    financial = svc._financial_gap(layers, layers["d04_ex"])
    operational = svc._operational_gap(layers, layers["d04_ex"])
    trust = svc._trust_challenge(layers, business, people, financial, operational)
    assert trust["trustTecnico"] >= 90
    assert trust["trustNegocio"] < trust["trustTecnico"]
    assert trust["gapTecnicoVsNegocio"] >= 10


def test_qa_refutes_d04_when_gap_material(svc: CoverageTruthAuditService):
    layers = svc._load_layers()
    business = svc._business_coverage(layers)
    prestacao = svc._prestacao_gap(layers)
    people = svc._people_challenge(layers, layers["d04_ex"])
    financial = svc._financial_gap(layers, layers["d04_ex"])
    operational = svc._operational_gap(layers, layers["d04_ex"])
    trust = svc._trust_challenge(layers, business, people, financial, operational)
    qa = svc._qa_certification(layers, trust, prestacao)
    assert qa["d04SuperestimouCobertura"] is True
    assert qa["classificacaoD04"] == "REFUTADO"


def test_build_full(svc: CoverageTruthAuditService):
    import asyncio

    resp = asyncio.run(svc.build("2026-06-01", "2026-06-07", None))
    assert resp.success
    data = resp.data
    assert data["sprint"] == "D04.1"
    assert data["fonte"]["adversarial"] is True
    assert "oQueSabemos" in data
    assert "oQueNaoSabemos" in data
    assert data["parecerFinal"].startswith("[PARECER FINAL:")
    assert "SUPERESTIMOU" in data["parecerFinal"]
