"""Testes D04 — Live Data Truth Baseline."""
from __future__ import annotations

import pytest

from src.services.live_data_truth_baseline_service import (
    AUTHORIZED_FILIAIS,
    LiveDataTruthBaselineService,
)


@pytest.fixture
def svc() -> LiveDataTruthBaselineService:
    return LiveDataTruthBaselineService()


@pytest.fixture
def layers(svc: LiveDataTruthBaselineService) -> dict:
    return svc._load_layers("2026-06-01", "2026-06-07")


def test_authorized_filiais():
    assert 11495 in AUTHORIZED_FILIAIS
    assert 5555 in AUTHORIZED_FILIAIS


def test_rejects_unauthorized_filial(svc: LiveDataTruthBaselineService):
    import asyncio

    resp = asyncio.run(svc.build("2026-06-01", "2026-06-07", 9999))
    assert not resp.success


def test_token_connectivity_audit(svc: LiveDataTruthBaselineService, layers: dict):
    audit = svc._token_connectivity_audit(layers, "2026-06-01", "2026-06-07")
    assert audit["operacional"] + audit["parcial"] + audit["indisponivel"] == len(audit["integrations"])
    assert audit["authorizedFiliais"] == list(AUTHORIZED_FILIAIS)


def test_financial_coverage(svc: LiveDataTruthBaselineService, layers: dict):
    fin = svc._financial_coverage(layers)
    assert 0 <= fin["coberturaPct"] <= 100
    assert fin["filiais11495"] or fin["filiais5555"]


def test_cash_coverage(svc: LiveDataTruthBaselineService, layers: dict):
    cash = svc._cash_coverage(layers)
    assert cash["coberturaPct"] >= 0
    assert cash["paridadePct"] in (0.0, 100.0)


def test_trust_baseline(svc: LiveDataTruthBaselineService, layers: dict):
    fin = svc._financial_coverage(layers)
    cash = svc._cash_coverage(layers)
    sales = svc._sales_coverage(layers)
    people = svc._workforce_coverage(layers)
    lineage = svc._lineage_consistency(layers)
    trust = svc._trust_baseline(fin, cash, sales, people, lineage)
    for key in (
        "financialTrustScore",
        "cashTrustScore",
        "salesTrustScore",
        "peopleTrustScore",
        "corporateTrustScore",
    ):
        assert 0 <= trust[key] <= 100
        assert trust[f"{key}Band"]


def test_build_full(svc: LiveDataTruthBaselineService):
    import asyncio

    resp = asyncio.run(svc.build("2026-06-01", "2026-06-07", None))
    assert resp.success
    data = resp.data
    assert data["sprint"] == "D04"
    assert data["fonte"]["webPostoLive"] is False
    assert "executiveAnswers" in data
    assert data["parecerFinal"].startswith("[PARECER FINAL:")
