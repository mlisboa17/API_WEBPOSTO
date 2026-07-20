from src.services.director_financial_reconciliation_snapshot_service import (
    DIRECTOR_RECONCILIATION_TTL_SECONDS,
    DirectorFinancialReconciliationSnapshotService,
)


class CountingPipeline:
    def __init__(self):
        self.calls = 0

    async def build(self, start, end, company):
        self.calls += 1
        return {"complete": True, "call": self.calls}


def snapshot_dir() -> str:
    return str(Path("tests/runtime_tmp") / f"director-reconciliation-test-{uuid4().hex}")


async def test_snapshot_reuses_fresh_payload() -> None:
    pipeline = CountingPipeline()
    service = DirectorFinancialReconciliationSnapshotService(pipeline, snapshot_dir())
    first, stale1, hit1 = await service.get_or_collect("2026-07-01", "2026-07-01", 11495)
    second, stale2, hit2 = await service.get_or_collect("2026-07-01", "2026-07-01", 11495)
    assert first == second
    assert pipeline.calls == 1
    assert (stale1, hit1) == (False, False)
    assert (stale2, hit2) == (False, True)


async def test_refresh_replaces_snapshot() -> None:
    pipeline = CountingPipeline()
    service = DirectorFinancialReconciliationSnapshotService(pipeline, snapshot_dir())
    await service.get_or_collect("2026-07-01", "2026-07-01", None)
    refreshed = await service.refresh("2026-07-01", "2026-07-01", None)
    assert refreshed["call"] == 2
    assert DIRECTOR_RECONCILIATION_TTL_SECONDS == 300.0
from pathlib import Path
from uuid import uuid4
