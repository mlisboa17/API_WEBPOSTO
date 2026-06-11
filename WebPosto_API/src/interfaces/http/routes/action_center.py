from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.action_center_service import ActionCenterService
from src.services.action_center_snapshot_service import ActionCenterSnapshotService

router = APIRouter(prefix="/api/v1/action-center", tags=["Action Center F05.2"])

_service = ActionCenterService()
_snapshot = ActionCenterSnapshotService(_service)


@router.get("/cockpit")
async def action_center_cockpit(
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
        "governanceRules": payload.get("governanceRules"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def action_center_summary(
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
            "executionTrackingEngine": payload.get("executionTrackingEngine"),
            "roiRealizationEngine": payload.get("roiRealizationEngine"),
        },
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/refresh")
async def action_center_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
