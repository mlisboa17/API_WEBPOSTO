from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.closed_loop_learning_engine_service import ClosedLoopLearningEngineService
from src.services.closed_loop_learning_engine_snapshot_service import (
    ClosedLoopLearningEngineSnapshotService,
)

router = APIRouter(prefix="/api/v1/closed-loop-learning", tags=["Closed Loop Learning F05.5"])

_service = ClosedLoopLearningEngineService()
_snapshot = ClosedLoopLearningEngineSnapshotService(_service)


@router.get("/cockpit")
async def closed_loop_learning_cockpit(
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
        "executiveFeedbackLoop": payload.get("executiveFeedbackLoop"),
        "learningEngine": payload.get("learningEngine"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def closed_loop_learning_summary(
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
            "outcomeMeasurementEngine": payload.get("outcomeMeasurementEngine"),
            "recommendationEffectivenessEngine": payload.get("recommendationEffectivenessEngine"),
        },
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/refresh")
async def closed_loop_learning_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
