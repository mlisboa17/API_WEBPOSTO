"""Testes F04.6 — Benchmark Intelligence."""
from __future__ import annotations

from pathlib import Path

from src.services.benchmark_intelligence_service import BenchmarkIntelligenceService, F045_AUDIT


def test_f045_audit_exists():
    assert F045_AUDIT.exists()


def test_load_layers():
    svc = BenchmarkIntelligenceService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    assert layers["f045"] or layers["f045_ex"]
    assert layers["f043"]


def test_company_benchmark():
    svc = BenchmarkIntelligenceService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    company = svc._company_benchmark(layers)
    assert company.get("filiais")
    assert company.get("melhorFilial")


def test_operator_benchmark_top20():
    svc = BenchmarkIntelligenceService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    ops = svc._operator_benchmark(layers)
    assert len(ops.get("top20") or []) <= 20
    assert ops.get("melhorOperador")


def test_qa_paridade_zero():
    svc = BenchmarkIntelligenceService()
    layers = svc._load_layers("2026-06-01", "2026-06-07")
    company = svc._company_benchmark(layers)
    operators = svc._operator_benchmark(layers)
    qa = svc._qa_engine(layers, company, operators, None)
    assert qa["paridadeZero"] is True
    assert qa["fonteWebPosto"] is False
