"""Testes unitários — inteligência avançada F01.4-B."""
from __future__ import annotations

from src.services.financial_intelligence_advanced_service import (
    _anomaly_severity,
    _benchmark_class,
    _pct,
    _q2,
)
from decimal import Decimal


def test_benchmark_classificacao() -> None:
    assert _benchmark_class(0.7) == "Excelente"
    assert _benchmark_class(0.95) == "Bom"
    assert _benchmark_class(1.1) == "Medio"
    assert _benchmark_class(1.5) == "Critico"


def test_anomaly_severity_sigma() -> None:
    assert _anomaly_severity(2.4) == "LOW"
    assert _anomaly_severity(2.6) == "MEDIUM"
    assert _anomaly_severity(3.2) == "HIGH"
    assert _anomaly_severity(4.1) == "CRITICAL"


def test_pct_helpers() -> None:
    assert _q2(Decimal("10.555")) == "10.56"
    assert _pct(Decimal("25"), Decimal("100")) == "25.00"
    assert _pct(Decimal("1"), Decimal("0")) == "0.00"
