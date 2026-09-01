"""Unit tests — Business Health Score (Sprint 2)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.interfaces.http.routes.owner_action_center import get_business_health
from src.services.decision_discovery.discovery_scope import DiscoveryScope, DiscoveryScopeService
from src.services.owner_business_health_service import (
    OwnerBusinessHealthService,
    _deduction_for_anomaly,
    _status_from_score,
)

ROOT = Path(__file__).resolve().parents[2]
OWNER_SNAPSHOT_DIR = ROOT / "snapshots" / "owner_analysis"


def _network_scope() -> DiscoveryScope:
    return DiscoveryScope(
        authorized_empresa_codes=frozenset({74014, 11495, 5555}),
        requested_empresa_codes=frozenset(),
        empresa_query=None,
    )


class _Request:
    headers: dict = {}
    cookies: dict = {}


def test_deduction_for_high_impact_anomaly():
    candidate = {
        "detector": "ExpenseDetector",
        "confidence": 0.9,
        "money_found": {"at_risk": {"value": 25000}},
    }
    points = _deduction_for_anomaly(candidate)
    assert 5 < points <= 15


def test_deduction_zero_without_impact():
    candidate = {"detector": "FuelRevenueDetector", "confidence": 0.9, "money_found": {}}
    assert _deduction_for_anomaly(candidate) == 0


def test_status_mapping():
    assert _status_from_score(85, True) == "healthy"
    assert _status_from_score(65, True) == "attention"
    assert _status_from_score(45, True) == "risk"
    assert _status_from_score(20, True) == "critical"
    assert _status_from_score(0, False) == "unknown"


@pytest.mark.skipif(
    not OWNER_SNAPSHOT_DIR.is_dir() or not any(OWNER_SNAPSHOT_DIR.glob("owner_analysis_last_valid_*.json")),
    reason="snapshot owner_analysis ausente",
)
def test_calculate_from_real_snapshot():
    service = OwnerBusinessHealthService()
    result = service.calculate("2026-07-01", "2026-07-11", scope=_network_scope())
    assert result.snapshot_hit is True
    assert result.overall_score >= 0
    assert result.risk_count >= 0
    if result.has_sufficient_data:
        assert result.overall_score > 0


@pytest.mark.asyncio
async def test_business_health_endpoint_integration():
    if not OWNER_SNAPSHOT_DIR.is_dir():
        pytest.skip("snapshot owner_analysis ausente")
    with patch.object(DiscoveryScopeService, "resolve", AsyncMock(return_value=_network_scope())):
        response = await get_business_health(
            _Request(),
            "2026-07-01",
            "2026-07-11",
            None,
        )
    assert response["success"] is True
    data = response["data"]
    assert "overall_score" in data
    assert "status" in data
    assert "risk_count" in data
