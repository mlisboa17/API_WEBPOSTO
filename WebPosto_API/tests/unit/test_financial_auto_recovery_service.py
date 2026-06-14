"""F08.2 — testes unitários de auto-recovery e scheduler (sem WebPosto live)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.financial_auto_recovery_service import FinancialAutoRecoveryService, RecoveryJob
from src.services.financial_snapshot_retention_service import FinancialSnapshotRetentionService
from src.services.financial_snapshot_scheduler import FinancialSnapshotScheduler
from src.services.financial_health_alert_service import FinancialHealthAlertService


class _FakeBreaker:
    def __init__(self) -> None:
        self._blocked = False

    def get_status(self, _key: str) -> str:
        return "OPEN" if self._blocked else "CLOSED"

    def is_blocked(self, _key: str) -> bool:
        return self._blocked

    def block_endpoint(self, _key: str, duration_seconds: int = 3600) -> None:
        self._blocked = True

    def reset(self, _key: str | None = None) -> None:
        self._blocked = False

    def record_success(self, _key: str) -> None:
        self._blocked = False


@pytest.fixture
def mock_scheduler() -> MagicMock:
    sched = MagicMock()
    sched.run_cycle = AsyncMock(
        return_value={
            "status": "completed",
            "results": [
                {"kind": "financial_overview", "success": True, "source": "snapshot_fallback"},
            ],
        }
    )
    return sched


@pytest.fixture
def recovery(mock_scheduler: MagicMock) -> FinancialAutoRecoveryService:
    svc = FinancialAutoRecoveryService(scheduler=mock_scheduler, snapshots=MagicMock())
    svc._client = MagicMock()
    svc._client.breaker = _FakeBreaker()
    return svc


def test_register_failure_creates_job(recovery: FinancialAutoRecoveryService):
    result = recovery.register_failure(
        snapshot_key="2026-06-01_2026-06-07_all",
        data_inicial="2026-06-01",
        data_final="2026-06-07",
    )
    assert result["registered"] is True
    status = recovery.get_recovery_status()
    assert status["pendingCount"] == 1


@pytest.mark.asyncio
async def test_attempt_recovery_keeps_snapshot_on_open_circuit(recovery: FinancialAutoRecoveryService):
    recovery.register_failure(
        snapshot_key="k1",
        data_inicial="2026-06-01",
        data_final="2026-06-07",
    )
    recovery._client.breaker.block_endpoint("despesas_financeiro_rede")
    outcome = await recovery.attempt_recovery("k1")
    assert outcome["success"] is False
    assert outcome["circuit"] == "OPEN"


@pytest.mark.asyncio
async def test_attempt_recovery_recovers_when_live_returns(recovery: FinancialAutoRecoveryService, mock_scheduler: MagicMock):
    recovery.register_failure(
        snapshot_key="k2",
        data_inicial="2026-06-01",
        data_final="2026-06-07",
    )
    mock_scheduler.run_cycle.return_value = {
        "results": [{"success": True, "source": "live"}],
    }
    outcome = await recovery.attempt_recovery("k2")
    assert outcome["success"] is True
    assert recovery.get_recovery_status()["recoveredCount"] == 1


def test_scheduler_schedule_next_run():
    sched = FinancialSnapshotScheduler(snapshots=MagicMock(), overview=MagicMock())
    nxt = sched.schedule_next_run()
    assert nxt is not None
    status = sched.get_scheduler_status()
    assert status["nextRunAt"] is not None
    assert status["enabled"] is True


@pytest.mark.asyncio
async def test_run_due_jobs_waits_before_interval():
    sched = FinancialSnapshotScheduler(snapshots=MagicMock(), overview=MagicMock())
    sched.schedule_next_run(from_time=datetime.now())
    result = await sched.run_due_jobs()
    assert result["ran"] is False
    assert result["status"] == "waiting"


def test_retention_protects_active_snapshot(tmp_path: Path):
    old = (datetime.now() - timedelta(days=40)).isoformat(timespec="seconds")
    active_key = "2026-06-01_2026-06-07_all"
    path = tmp_path / f"financial_overview_{active_key}.json"
    path.write_text(
        f'{{"kind":"financial_overview","key":"{active_key}","lastUpdated":"{old}","data":{{"postos":[]}}}}',
        encoding="utf-8",
    )
    svc = FinancialSnapshotRetentionService(tmp_path)
    svc.set_active_snapshot_key(active_key)
    expired = svc.list_expired_snapshots(30)
    assert expired[0]["protected"] is True
    result = svc.apply_retention(30)
    assert result["removedCount"] == 0
    assert path.exists()


def test_alerts_have_origin():
    health = MagicMock()
    health.assess_key.return_value = {
        "summary": {"coverageComplete": True, "overallStatus": "HEALTHY"},
        "snapshots": [],
    }
    alerts = FinancialHealthAlertService(health=health).generate("2026-06-01", "2026-06-07")
    assert alerts
    assert all(alert.get("origin") for alert in alerts)


def test_scheduler_module_has_no_import_loop():
    from src.services import financial_snapshot_scheduler as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "while True" not in source
    assert "start_background" not in source
