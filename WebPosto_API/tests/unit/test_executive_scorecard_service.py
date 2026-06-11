"""Testes F04.7 — Executive Scorecard."""
from __future__ import annotations

from src.services.executive_scorecard_service import (
    ExecutiveScorecardService,
    F045_AUDIT,
    F046_AUDIT,
)


def test_audits_exist():
    assert F045_AUDIT.exists()
    assert F046_AUDIT.exists()


def test_executive_kpi_scores():
    svc = ExecutiveScorecardService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    kpis = svc._executive_kpi_engine(layers)
    assert 0 <= kpis["executiveScore"] <= 100
    assert kpis["financialScore"] >= 0


def test_alerts_have_evidence():
    svc = ExecutiveScorecardService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    kpis = svc._executive_kpi_engine(layers)
    alerts = svc._executive_alert_engine(layers, kpis)
    assert alerts
    assert all(a.get("reference") or a.get("evidence") for a in alerts)


def test_qa_paridade():
    svc = ExecutiveScorecardService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    kpis = svc._executive_kpi_engine(layers)
    alerts = svc._executive_alert_engine(layers, kpis)
    qa = svc._qa_engine(layers, kpis, alerts, None)
    assert qa["paridadeZero"] is True
    assert qa["fonteWebPosto"] is False


def test_trend_classification():
    svc = ExecutiveScorecardService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    kpis = svc._executive_kpi_engine(layers)
    trends = svc._trend_forecast_engine(layers, kpis)
    assert trends["operacaoGeral"] in ("MELHORANDO", "ESTAVEL", "PIORANDO")
