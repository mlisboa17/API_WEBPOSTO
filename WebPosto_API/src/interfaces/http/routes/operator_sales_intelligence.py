from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.operator_sales_intelligence_service import OperatorSalesIntelligenceService
from src.services.operator_sales_intelligence_snapshot_service import OperatorSalesIntelligenceSnapshotService

router = APIRouter(prefix="/api/v1/operator-intelligence", tags=["Operator Intelligence F04.0"])

_intel = OperatorSalesIntelligenceService()
_snapshot = OperatorSalesIntelligenceSnapshotService(_intel)


@router.get("/snapshot")
async def intelligence_snapshot(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None, "error": "Falha ao consolidar operator intelligence"}
    return {
        "success": True,
        "data": payload,
        "snapshot": {"hit": hit, "stale": stale},
        "error": None,
    }


@router.post("/refresh")
async def intelligence_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}


@router.get("/cockpit")
async def intelligence_cockpit(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None}
    return {
        "success": True,
        "data": payload.get("cockpit"),
        "executiveAnswers": payload.get("executiveAnswers"),
        "parecerFinal": payload.get("parecerFinal"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/employees")
async def intelligence_employees(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
) -> dict:
    payload, _, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, None)
    if not payload:
        return {"success": False, "data": None}
    return {"success": True, "data": payload.get("dimEmployee"), "snapshot": {"hit": hit}}


@router.get("/summary")
async def intelligence_summary(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None}
    return {
        "success": True,
        "data": {
            "executiveAnswers": payload.get("executiveAnswers"),
            "qa": payload.get("qa"),
            "parecerFinal": payload.get("parecerFinal"),
            "periodo": payload.get("periodo"),
        },
        "snapshot": {"hit": hit, "stale": stale},
    }
