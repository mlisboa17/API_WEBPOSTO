from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query

from src.services.cash_operations_service import CashOperationsService
from src.services.cash_operations_snapshot_service import CashOperationsSnapshotService

router = APIRouter(prefix="/api/v1/cash/operations", tags=["Cash Operations"])

_operations = CashOperationsService()
_snapshot = CashOperationsSnapshotService(_operations)


def _query_params(
    dataInicial: str,
    dataFinal: str,
    empresaCodigo: str | None,
) -> tuple[str, str, str | None]:
    return dataInicial, dataFinal, empresaCodigo


@router.get("/summary")
async def cash_operations_summary(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    di, df, emp = _query_params(dataInicial, dataFinal, empresaCodigo)
    data, stale = await _snapshot.get_or_collect(di, df, emp)
    if not data:
        return {"success": False, "data": None, "error": "Falha ao consolidar cash operations"}
    return {
        "success": True,
        "data": {
            **data.get("summary", {}),
            "periodo": data.get("periodo"),
            "fromSnapshot": not stale,
            "performanceMs": data.get("performanceMs"),
        },
        "error": None,
    }


@router.get("/alerts")
async def cash_operations_alerts(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    di, df, emp = _query_params(dataInicial, dataFinal, empresaCodigo)
    data, _ = await _snapshot.get_or_collect(di, df, emp)
    return {"success": bool(data), "data": data.get("alerts") if data else None, "error": None}


@router.get("/operators")
async def cash_operations_operators(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    di, df, emp = _query_params(dataInicial, dataFinal, empresaCodigo)
    data, _ = await _snapshot.get_or_collect(di, df, emp)
    return {"success": bool(data), "data": data.get("operators") if data else None, "error": None}


@router.get("/pdvs")
async def cash_operations_pdvs(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    di, df, emp = _query_params(dataInicial, dataFinal, empresaCodigo)
    data, _ = await _snapshot.get_or_collect(di, df, emp)
    return {"success": bool(data), "data": data.get("pdvs") if data else None, "error": None}


@router.get("/turns")
async def cash_operations_turns(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    di, df, emp = _query_params(dataInicial, dataFinal, empresaCodigo)
    data, _ = await _snapshot.get_or_collect(di, df, emp)
    return {"success": bool(data), "data": data.get("turns") if data else None, "error": None}


@router.get("/risk-score")
async def cash_operations_risk_score(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    di, df, emp = _query_params(dataInicial, dataFinal, empresaCodigo)
    data, _ = await _snapshot.get_or_collect(di, df, emp)
    return {"success": bool(data), "data": data.get("riskScore") if data else None, "error": None}


@router.get("/snapshot")
async def cash_operations_snapshot(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    di, df, emp = _query_params(dataInicial, dataFinal, empresaCodigo)
    master = _snapshot.get_master(di, df, emp)
    if master.get("stale") and master.get("operations"):
        asyncio.create_task(_snapshot.refresh_background(di, df, emp))
    return {"success": True, "data": master, "error": None}


@router.post("/refresh")
async def cash_operations_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    di, df, emp = _query_params(dataInicial, dataFinal, empresaCodigo)
    asyncio.create_task(_snapshot.refresh_background(di, df, emp))
    return {"success": True, "data": {"status": "refresh_started"}, "error": None}
