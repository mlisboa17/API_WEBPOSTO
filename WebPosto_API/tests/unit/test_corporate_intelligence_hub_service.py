"""Testes F05.0 — Corporate Intelligence Hub."""
from __future__ import annotations

from src.services.corporate_intelligence_hub_service import (
    CorporateIntelligenceHubService,
    F045_AUDIT,
    F046_AUDIT,
    F047_AUDIT,
)


def test_audits_exist():
    assert F045_AUDIT.exists()
    assert F046_AUDIT.exists()
    assert F047_AUDIT.exists()


def test_corporate_score():
    svc = CorporateIntelligenceHubService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    kpis = svc._corporate_kpi_consolidation(layers)
    assert 0 < kpis["corporateScore"] <= 100
    assert kpis["paridadeDelta"] == 0.0


def test_opportunity_engine():
    svc = CorporateIntelligenceHubService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    kpis = svc._corporate_kpi_consolidation(layers)
    fin = svc._financial_hub(layers, kpis)
    people = svc._people_hub(layers)
    ops = svc._operations_hub(layers)
    opps = svc._opportunity_engine(kpis, fin, people, ops)
    assert opps["opportunities"]
    assert all(o.get("calculo") for o in opps["opportunities"])


def test_risk_engine():
    svc = CorporateIntelligenceHubService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    kpis = svc._corporate_kpi_consolidation(layers)
    people = svc._people_hub(layers)
    ops = svc._operations_hub(layers)
    risks = svc._risk_engine(layers, kpis, people, ops)
    assert risks["risks"]
    assert all(r.get("justificativa") for r in risks["risks"])


def test_qa_lineage():
    svc = CorporateIntelligenceHubService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    kpis = svc._corporate_kpi_consolidation(layers)
    fin = svc._financial_hub(layers, kpis)
    people = svc._people_hub(layers)
    ops = svc._operations_hub(layers)
    opps = svc._opportunity_engine(kpis, fin, people, ops)
    risks = svc._risk_engine(layers, kpis, people, ops)
    qa = svc._qa_governance(layers, kpis, opps, risks, None)
    assert qa["paridadeZero"] is True
    assert qa["lineage"]
