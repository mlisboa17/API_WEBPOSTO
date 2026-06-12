from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.commercial_execution_snapshot_service import CommercialExecutionSnapshotService
from src.services.commercial_execution_service import CommercialExecutionService

router = APIRouter(prefix="/api/v1/commercial-execution", tags=["Commercial Execution F07.7"])

_service = CommercialExecutionService()
_snapshot = CommercialExecutionSnapshotService(_service)


@router.get("/cockpit")
async def commercial_execution_cockpit(
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
        "commercialAssignmentEngine": payload.get("commercialAssignmentEngine"),
        "commercialExecutionTracking": payload.get("commercialExecutionTracking"),
        "commercialEvidenceEngine": payload.get("commercialEvidenceEngine"),
        "commercialOutcomeMeasurement": payload.get("commercialOutcomeMeasurement"),
        "revenueLiftTracking": payload.get("revenueLiftTracking"),
        "marginImprovementTracking": payload.get("marginImprovementTracking"),
        "commercialPerformance": payload.get("commercialPerformance"),
        "fonte": payload.get("fonte"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def commercial_execution_summary(
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
async def commercial_execution_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
