import asyncio
from datetime import date
from types import SimpleNamespace

from src.services.periodic_audit_cycle_store import PeriodicAuditCycleStore
from src.services.periodic_audit_scheduler_service import PeriodicAuditSchedulerService


class FakeRuns:
    def __init__(self):
        self.calls = []

    async def open_run(self, cycle, company, center, start, end):
        self.calls.append((cycle, company, center, start, end))
        return SimpleNamespace(id=f"run-{cycle}")


def test_scheduler_opens_only_due_active_cycles_and_uses_previous_window(tmp_path):
    cycles = PeriodicAuditCycleStore(tmp_path / "cycles.json")
    due = cycles.create("5555", "PISTA", 7, "Diretoria", date(2026, 7, 27))
    paused = cycles.create("11495", "PISTA", 7, "Diretoria", date(2026, 7, 27))
    cycles.set_active(paused.id, False)
    runs = FakeRuns()
    result = asyncio.run(PeriodicAuditSchedulerService(cycles, runs).run_due("2026-07-27"))

    assert result["opened"] == 1
    assert runs.calls == [(due.id, "5555", "PISTA", "2026-07-20", "2026-07-26")]
