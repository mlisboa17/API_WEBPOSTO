"""Testes F06.3 — Tax & Product Fiscal Intelligence."""
from __future__ import annotations

import pytest

from src.services.tax_product_fiscal_intelligence_service import (
    RISK_LEVELS,
    TAX_LEVELS,
    TaxProductFiscalIntelligenceService,
)


def test_tax_and_risk_levels_complete():
    assert len(TAX_LEVELS) == 3
    assert len(RISK_LEVELS) == 4


def test_evidenced_products_have_lineage():
    svc = TaxProductFiscalIntelligenceService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    assert layers["products"]
    for product in layers["products"]:
        assert product.get("lineage")
        assert product.get("fiscalProductId")


def test_ncm_not_invented_for_unknown_products():
    svc = TaxProductFiscalIntelligenceService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    ncm = svc._ncm_intelligence_engine(layers)
    for row in ncm.get("ausentes") or []:
        prod = next((p for p in layers["products"] if p.get("produtoCodigo") == row.get("produtoCodigo")), {})
        assert not prod.get("ncm")


def test_tax_classification_partial_not_invented():
    svc = TaxProductFiscalIntelligenceService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    tax = svc._tax_classification_engine(layers)
    assert tax["coberturaTributaria"] == "PARCIAL"
    for item in tax["items"]:
        assert item["classificacao"] in TAX_LEVELS


@pytest.mark.asyncio
async def test_build_full_payload():
    svc = TaxProductFiscalIntelligenceService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F06.3"
    assert data["fonte"]["webPostoLive"] is False
    qa = data["qa"]
    assert qa["fonteWebPostoLive"] is False
    assert qa["semNcmInventado"] is True
    assert qa["semClassificacaoInventada"] is True
    assert qa["motorAuditavel"] is True
    assert qa["lineageCompleto"] is True
    assert qa["semProdutoSemLineage"] is True
    assert qa["semCalculoFiscalSemOrigem"] is True
    ex = data["executiveAnswers"]
    assert ex["1_totalProdutos"] == 200
    assert ex["4_coberturaTributaria"] == "PARCIAL"
    assert ex["5_coberturaFinanceira"] == "PARCIAL"
    assert ex["9_dreViavel"] is True
    assert ex["10_centroCustoViavel"] is False
    assert ex["16_motorAuditavel"] is True
    assert ex["17_lineageCompleto"] is True
    assert ex["19_fiscalIntelligenceMadura"] is True
    assert ex["20_aprovadoF064"] is True
    assert data["parecerFinal"] == "[PARECER FINAL: APROVADO PARA F06.4]"
