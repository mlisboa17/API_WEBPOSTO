"""F08.3 — API read-only do Financial Operations Center."""
from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.financial_operations_center_service import get_operations_center_service

router = APIRouter(prefix="/api/v1/financial/operations-center", tags=["Financial Operations Center F08.3"])

_center = get_operations_center_service()


@router.get("/summary")
async def operations_center_summary(
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    empresaCodigo: str | None = Query(None),
) -> dict:
    data = _center.get_operations_summary(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": data, "error": None}


@router.get("/status")
async def operations_center_status(
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    empresaCodigo: str | None = Query(None),
) -> dict:
    data = _center.get_operational_status(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": data, "error": None}


@router.get("/alerts")
async def operations_center_alerts(
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    empresaCodigo: str | None = Query(None),
) -> dict:
    data = _center.get_operational_alerts(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": data, "error": None}


@router.get("/executions")
async def operations_center_executions(
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    empresaCodigo: str | None = Query(None),
    limit: int = Query(50, le=200),
) -> dict:
    data = _center.get_executions(limit, dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": data, "error": None}


@router.get("/cockpit")
async def operations_center_cockpit(
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    empresaCodigo: str | None = Query(None),
) -> dict:
    data = _center.get_full_cockpit(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": data, "error": None}


@router.get("/timeline")
async def operations_center_timeline(
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    empresaCodigo: str | None = Query(None),
) -> dict:
    data = _center.get_timeline(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": data, "error": None}


@router.get("/dw-export")
async def operations_center_dw_export(
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    empresaCodigo: str | None = Query(None),
) -> dict:
    row = _center.dw_row(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": {"rows": [row], "total": 1}, "error": None}
