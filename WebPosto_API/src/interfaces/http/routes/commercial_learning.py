from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.commercial_learning_service import CommercialLearningService
from src.services.commercial_learning_snapshot_service import CommercialLearningSnapshotService

router = APIRouter(prefix="/api/v1/commercial-learning", tags=["Commercial Learning F07.8"])

_service = CommercialLearningService()
_snapshot = CommercialLearningSnapshotService(_service)


@router.get("/cockpit")
async def commercial_learning_cockpit(
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
        "recommendationEffectivenessEngine": payload.get("recommendationEffectivenessEngine"),
        "responsiblePerformanceEngine": payload.get("responsiblePerformanceEngine"),
        "branchLearningEngine": payload.get("branchLearningEngine"),
        "recommendationCalibrationEngine": payload.get("recommendationCalibrationEngine"),
        "outcomeLearningEngine": payload.get("outcomeLearningEngine"),
        "executiveLearningReport": payload.get("executiveLearningReport"),
        "fonte": payload.get("fonte"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def commercial_learning_summary(
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
            "dwLayer": payload.get("dwLayer"),
        },
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/refresh")
async def commercial_learning_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
