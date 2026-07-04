"""Single-flight atômico por scope — PERFORMANCE-01."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.services.owner_analysis_snapshot_service import OwnerAnalysisSnapshotService


@pytest.fixture
def service(tmp_path) -> OwnerAnalysisSnapshotService:
    return OwnerAnalysisSnapshotService(
        output_dir=str(tmp_path / "owner_analysis"),
        freshness_ttl_seconds=1800,
    )


@pytest.mark.asyncio
async def test_concurrent_trigger_same_scope_returns_one_analysis_id(service: OwnerAnalysisSnapshotService) -> None:
    with patch.object(service, "_run_refresh", new=AsyncMock()):
        results = await asyncio.gather(
            service.trigger_refresh("2026-06-27", "2026-07-04", reason="t1"),
            service.trigger_refresh("2026-06-27", "2026-07-04", reason="t2"),
            service.trigger_refresh("2026-06-27", "2026-07-04", reason="t3"),
            service.trigger_refresh("2026-06-27", "2026-07-04", reason="t4"),
            service.trigger_refresh("2026-06-27", "2026-07-04", reason="t5"),
        )

    ids = {r["analysis_id"] for r in results}
    assert len(ids) == 1
    assert sum(1 for r in results if r["already_running"] is False) == 1
    assert sum(1 for r in results if r["already_running"] is True) == 4
    assert len(service._jobs) == 1


@pytest.mark.asyncio
async def test_different_scopes_get_different_analysis_ids(service: OwnerAnalysisSnapshotService) -> None:
    with patch.object(service, "_run_refresh", new=AsyncMock()):
        r_all = await service.trigger_refresh("2026-06-27", "2026-07-04")
        r_one = await service.trigger_refresh("2026-06-27", "2026-07-04", empresa_codigo="5555")

    assert r_all["analysis_id"] != r_one["analysis_id"]
    assert r_all["already_running"] is False
    assert r_one["already_running"] is False
    assert len(service._jobs) == 2
