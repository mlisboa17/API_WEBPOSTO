"""F08.1 — API de saúde e monitoramento de snapshots financeiros."""
from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.financial_snapshot_health_service import FinancialSnapshotHealthService

router = APIRouter(prefix="/api/v1/financial/snapshot-health", tags=["Financial Snapshot Health F08.1"])

_health = FinancialSnapshotHealthService()


@router.get("/inventory")
async def snapshot_inventory() -> dict:
    items = _health.inventory()
    return {"success": True, "data": {"items": items, "total": len(items)}, "error": None}


@router.get("/assessment")
async def snapshot_assessment(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    data = _health.assess_key(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": data, "error": None}


@router.get("/cockpit")
async def snapshot_cockpit(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    data = _health.cockpit(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": data, "error": None}


@router.get("/dw-export")
async def snapshot_dw_export(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    rows = _health.dw_rows(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": {"rows": rows, "total": len(rows)}, "error": None}
