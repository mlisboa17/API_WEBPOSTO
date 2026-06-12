"""Testes F07.0A — Product Coverage Truth Audit."""
from __future__ import annotations

import pytest

from src.services.product_coverage_truth_audit_service import (
    CATEGORIES,
    ProductCoverageTruthAuditService,
)


def test_categories_defined():
    assert "COMBUSTIVEL" in CATEGORIES
    assert "NAO_CLASSIFICADO" in CATEGORIES


def test_classify_fuel_by_bico():
    svc = ProductCoverageTruthAuditService()
    cls = svc._classify(999999, {}, {"bicoCodigo": 42902})
    assert cls["categoria"] == "COMBUSTIVEL"
    assert cls["confidence"] == "ALTA"


def test_classify_loja_by_catalog():
    svc = ProductCoverageTruthAuditService()
    catalog = {1803673: {"produtoCodigo": 1803673, "nome": "Item loja", "combustivel": False, "tipoProduto": "L"}}
    cls = svc._classify(1803673, catalog, {"produtoCodigo": 1803673, "totalVenda": 3.99})
    assert cls["categoria"] == "LOJA"


@pytest.mark.asyncio
async def test_build_offline_payload():
    svc = ProductCoverageTruthAuditService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F07.0A"
    qa = data["qa"]
    assert qa["semClassificacaoInventada"] is True
    assert qa["tudoBaseadoEvidencia"] is True
    assert data["revenueCoverageAudit"]["receitaNaoCombustivelF070"] == 462.84
    assert data["parecerFinal"].startswith("[PARECER FINAL:")
