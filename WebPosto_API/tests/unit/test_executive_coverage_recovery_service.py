"""Testes D05 — Executive Coverage Recovery."""
from __future__ import annotations

import pytest

from src.services.executive_coverage_recovery_service import AUTHORIZED_FILIAIS, ExecutiveCoverageRecoveryService


@pytest.fixture
def svc() -> ExecutiveCoverageRecoveryService:
    return ExecutiveCoverageRecoveryService()


def test_rejects_unauthorized_filial(svc: ExecutiveCoverageRecoveryService):
    import asyncio

    resp = asyncio.run(svc.build("2026-06-01", "2026-06-07", 9999))
    assert not resp.success


def test_participation_convergence(svc: ExecutiveCoverageRecoveryService):
    layers = svc._load_layers()
    part = svc._participation_discovery(layers)
    assert part["convergenciaPct"] >= 98
    assert part["classificacao"] == "EQUIVALENTE"


def test_recovery_meets_acceptance(svc: ExecutiveCoverageRecoveryService):
    import asyncio

    resp = asyncio.run(svc.build("2026-06-01", "2026-06-07", None))
    assert resp.success
    rec = resp.data["executiveCoverageRecalculation"]
    depois = rec["depois"]
    assert depois["trustNegocio"] > 80
    assert depois["trustExecutivo"] > 70
    assert resp.data["qaCertification"]["aprovado"] is True
    assert "RECUPERADA" in resp.data["parecerFinal"]


def test_lmc_main_endpoint(svc: ExecutiveCoverageRecoveryService):
    layers = svc._load_layers()
    lmc = svc._lmc_recovery(layers)
    assert lmc["httpStatus"] == 200
    assert lmc["registros"] > 0


def test_build_executive_answers(svc: ExecutiveCoverageRecoveryService):
    import asyncio

    resp = asyncio.run(svc.build("2026-06-01", "2026-06-07", None))
    ex = resp.data["executiveAnswers"]
    assert ex["20_f051Liberado"] is True
    assert len(ex["15_gapsEliminados"]) >= 3
    assert list(AUTHORIZED_FILIAIS) == [11495, 5555]
