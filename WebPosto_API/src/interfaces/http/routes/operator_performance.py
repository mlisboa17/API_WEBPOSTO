from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query

from src.services.operator_performance_service import OperatorPerformanceService
from src.services.operator_performance_snapshot_service import OperatorPerformanceSnapshotService

router = APIRouter(prefix="/api/v1/performance", tags=["Operator Performance"])

_performance = OperatorPerformanceService()
_snapshot = OperatorPerformanceSnapshotService(_performance)


def _params(dataInicial: str, dataFinal: str, empresaCodigo: str | None) -> tuple[str, str, str | None]:
    return dataInicial, dataFinal, empresaCodigo


@router.get("/operators")
async def performance_operators(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    di, df, emp = _params(dataInicial, dataFinal, empresaCodigo)
    payload, stale, hit = await _snapshot.get_or_collect(di, df, emp)
    if not payload:
        return {"success": False, "data": None, "error": "Falha ao consolidar performance de operadores"}
    return {
        "success": True,
        "data": payload.get("operators"),
        "summary": payload.get("summary"),
        "snapshot": {"hit": hit, "stale": stale},
        "error": None,
    }


@router.get("/pdvs")
async def performance_pdvs(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    di, df, emp = _params(dataInicial, dataFinal, empresaCodigo)
    payload, stale, hit = await _snapshot.get_or_collect(di, df, emp)
    if not payload:
        return {"success": False, "data": None, "error": "Falha ao consolidar performance de PDVs"}
    return {
        "success": True,
        "data": payload.get("pdvs"),
        "snapshot": {"hit": hit, "stale": stale},
        "error": None,
    }


@router.get("/turns")
async def performance_turns(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    di, df, emp = _params(dataInicial, dataFinal, empresaCodigo)
    payload, stale, hit = await _snapshot.get_or_collect(di, df, emp)
    if not payload:
        return {"success": False, "data": None, "error": "Falha ao consolidar performance de turnos"}
    return {
        "success": True,
        "data": payload.get("turns"),
        "snapshot": {"hit": hit, "stale": stale},
        "error": None,
    }


@router.get("/summary")
async def performance_summary(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    di, df, emp = _params(dataInicial, dataFinal, empresaCodigo)
    payload, stale, hit = await _snapshot.get_or_collect(di, df, emp)
    if not payload:
        return {"success": False, "data": None, "error": "Falha ao consolidar performance"}
    return {
        "success": True,
        "data": {
            **(payload.get("summary") or {}),
            "periodo": payload.get("periodo"),
            "evolution": payload.get("evolution"),
            "bestPractices": payload.get("bestPractices"),
            "criticalFocus": payload.get("criticalFocus"),
            "performanceMs": payload.get("performanceMs"),
        },
        "snapshot": {"hit": hit, "stale": stale},
        "error": None,
    }


@router.get("/snapshot")
async def performance_snapshot(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    di, df, emp = _params(dataInicial, dataFinal, empresaCodigo)
    master = _snapshot.get_master(di, df, emp)
    if master.get("stale") and master.get("payload"):
        asyncio.create_task(_snapshot.refresh_background(di, df, emp))
    return {"success": True, "data": master, "error": None}


@router.get("/context-attribution")
async def performance_context_attribution(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    di, df, emp = _params(dataInicial, dataFinal, empresaCodigo)
    payload, stale, hit = await _snapshot.get_or_collect(di, df, emp)
    if not payload:
        return {"success": False, "data": None, "error": "Falha ao consolidar atribuição de contexto"}
    return {
        "success": True,
        "data": payload.get("contextAttribution"),
        "snapshot": {"hit": hit, "stale": stale},
        "error": None,
    }


@router.post("/refresh")
async def performance_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
    includeWindows: bool = Query(False),
) -> dict:
    di, df, emp = _params(dataInicial, dataFinal, empresaCodigo)
    asyncio.create_task(_snapshot.refresh_background(di, df, emp, includeWindows))
    return {"success": True, "data": {"status": "refresh_started"}, "error": None}
