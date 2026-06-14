"""Unit tests — F08.4 Financial Intelligence Center."""
from __future__ import annotations

from src.services.financial_intelligence_evidence import classify_executive_score, classify_trend, delta_pct
from src.services.financial_intelligence_center_service import (
    FinancialIntelligenceCenterService,
    _compute_executive_financial_score,
    _score_liquidity,
    _score_risks,
)
from src.services.financial_intelligence_evidence import PeriodMetrics
from decimal import Decimal


def test_classify_trend_bands():
    assert classify_trend(10) == "CRESCIMENTO"
    assert classify_trend(0) == "ESTABILIDADE"
    assert classify_trend(-10) == "QUEDA"
    assert classify_trend(None) == "INDETERMINADO"


def test_executive_score_weights():
    result = _compute_executive_financial_score(
        liquidity=100,
        fluxo=100,
        receivables=100,
        despesas=100,
        risks=100,
    )
    assert result["score"] == 100.0
    assert result["classification"] == "EXCELENTE"
    assert result["components"]["liquidity"] == 25.0


def test_score_liquidity():
    metrics = PeriodMetrics(
        despesas=Decimal("100"),
        pagamentos=Decimal("50"),
        recebimentos=Decimal("100"),
        receitas=Decimal("100"),
        fluxo=Decimal("0"),
        receivable_rows=1,
        payable_rows=1,
        overdue_receivables=Decimal("0"),
        overdue_payables=Decimal("0"),
        expense_concentration_top_share=10.0,
        receivable_top_share=10.0,
    )
    assert _score_liquidity(metrics) >= 70


def test_delta_pct():
    assert delta_pct(Decimal("110"), Decimal("100")) == 10.0


def test_intelligence_cockpit_snapshot_first():
    svc = FinancialIntelligenceCenterService()
    data = svc.get_cockpit("2026-06-01", "2026-06-07")
    assert data["snapshotFirst"] is True
    assert data["generativeAi"] is False
    assert data["executiveFinancialScore"]["score"] is not None
    assert len(data["executiveCards"]) <= 6
    assert "trends" in data
    assert "risks" in data
    assert "opportunities" in data
    assert data["cashFlow"]["forecast"] is None


def test_risk_lineage_present():
    svc = FinancialIntelligenceCenterService()
    data = svc.get_cockpit("2026-06-01", "2026-06-07")
    for risk in data["risks"]["risks"]:
        assert "lineage" in risk


def test_opportunity_has_required_fields():
    svc = FinancialIntelligenceCenterService()
    data = svc.get_cockpit("2026-06-01", "2026-06-07")
    for opp in data["opportunities"]["opportunities"]:
        assert "impacto_estimado" in opp
        assert "evidencia" in opp
        assert "origem" in opp


def test_classify_executive_score():
    assert classify_executive_score(95) == "EXCELENTE"
    assert classify_executive_score(40) == "CRÍTICO"


def test_score_risks():
    assert _score_risks({"overallLevel": "CRÍTICO"}) == 20.0
