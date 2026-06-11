from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.management_action_center_service import ManagementActionCenterService
from src.services.management_action_center_snapshot_service import ManagementActionCenterSnapshotService

router = APIRouter(prefix="/api/v1/management-action", tags=["Management Action Center F04.4"])

_service = ManagementActionCenterService()
_snapshot = ManagementActionCenterSnapshotService(_service)


@router.get("/snapshot")
async def management_snapshot(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None, "error": "Falha ao consolidar Management Action Center"}
    return {
        "success": True,
        "data": payload,
        "snapshot": {"hit": hit, "stale": stale},
        "error": None,
    }


@router.post("/refresh")
async def management_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}


@router.get("/cockpit")
async def management_cockpit(
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
async def management_summary(
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
