from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.operator_profitability_service import OperatorProfitabilityService
from src.services.operator_profitability_snapshot_service import OperatorProfitabilitySnapshotService

router = APIRouter(prefix="/api/v1/people-roi", tags=["People ROI F04.2"])

_service = OperatorProfitabilityService()
_snapshot = OperatorProfitabilitySnapshotService(_service)


@router.get("/snapshot")
async def roi_snapshot(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None, "error": "Falha ao consolidar people ROI"}
    return {
        "success": True,
        "data": payload,
        "snapshot": {"hit": hit, "stale": stale},
        "error": None,
    }


@router.post("/refresh")
async def roi_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}


@router.get("/cockpit")
async def roi_cockpit(
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
        "qa": payload.get("qa"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def roi_summary(
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
