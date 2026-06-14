"""F08.2 — API operacional: scheduler, recovery, alertas e simulação."""
from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.financial_auto_recovery_service import get_financial_auto_recovery
from src.services.financial_operations_service import get_operations_service
from src.services.financial_snapshot_execution_store import get_execution_store
from src.services.financial_snapshot_retention_service import get_retention_service
from src.services.financial_snapshot_scheduler import get_financial_scheduler

router = APIRouter(prefix="/api/v1/financial/operations", tags=["Financial Operations F08.2"])

_operations = get_operations_service()
_scheduler = get_financial_scheduler()
_recovery = get_financial_auto_recovery()


@router.get("/status")
async def operations_status(
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    empresaCodigo: str | None = Query(None),
) -> dict:
    data = await _operations.cockpit(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": data, "error": None}


@router.post("/run-now")
async def operations_run_now(
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    empresaCodigo: str | None = Query(None),
) -> dict:
    _scheduler.schedule_next_run(from_time=None)
    result = await _scheduler.run_cycle(dataInicial, dataFinal, empresaCodigo, trigger="manual")
    _scheduler.schedule_next_run()
    return {"success": True, "data": result, "error": None}


@router.post("/tick")
async def operations_tick() -> dict:
    sched = await _scheduler.run_due_jobs()
    rec = await _recovery.run_due_recoveries()
    return {"success": True, "data": {"scheduler": sched, "recovery": rec}, "error": None}


@router.post("/retention/apply")
async def operations_retention_apply() -> dict:
    result = get_retention_service().apply_retention()
    return {"success": True, "data": result, "error": None}


@router.post("/simulate-recovery")
async def operations_simulate_recovery(scenario: str = Query(...)) -> dict:
    result = await _recovery.simulate(scenario)
    return {"success": bool(result.get("success")), "data": result, "error": None}


@router.get("/executions")
async def operations_executions(limit: int = Query(50, le=200)) -> dict:
    rows = get_execution_store().list_recent(limit)
    return {"success": True, "data": {"rows": rows, "total": len(rows)}, "error": None}


@router.get("/dw-export")
async def operations_dw_export(limit: int = Query(100, le=500)) -> dict:
    rows = get_execution_store().dw_rows(limit)
    return {"success": True, "data": {"rows": rows, "total": len(rows)}, "error": None}
