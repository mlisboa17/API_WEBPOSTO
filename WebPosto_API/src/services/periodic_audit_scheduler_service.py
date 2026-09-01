"""Orquestra abertura idempotente dos ciclos periódicos vencidos."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from src.services.periodic_audit_cycle_store import PeriodicAuditCycleStore
from src.services.periodic_audit_run_service import PeriodicAuditRunService


class PeriodicAuditSchedulerService:
    def __init__(
        self,
        cycles: PeriodicAuditCycleStore | None = None,
        runs: PeriodicAuditRunService | None = None,
    ) -> None:
        self._cycles = cycles or PeriodicAuditCycleStore()
        self._runs = runs or PeriodicAuditRunService()

    async def run_due(self, reference_day: str | None = None) -> dict[str, Any]:
        current = date.fromisoformat(reference_day) if reference_day else date.today()
        results = []
        for cycle in self._cycles.list_all():
            if not cycle.ativo or cycle.proxima_auditoria(current) != current:
                continue
            end = current - timedelta(days=1)
            start = end - timedelta(days=cycle.periodicidade_dias - 1)
            try:
                run = await self._runs.open_run(
                    cycle.id,
                    cycle.empresa_codigo,
                    cycle.centro_custo,
                    start.isoformat(),
                    end.isoformat(),
                )
                results.append({"cycleId": cycle.id, "runId": run.id, "success": True})
            except Exception as exc:  # noqa: BLE001
                results.append({"cycleId": cycle.id, "runId": None, "success": False, "error": str(exc)[:200]})
        return {
            "referenceDay": current.isoformat(),
            "dueCycles": len(results),
            "opened": sum(item["success"] for item in results),
            "failed": sum(not item["success"] for item in results),
            "results": results,
        }
