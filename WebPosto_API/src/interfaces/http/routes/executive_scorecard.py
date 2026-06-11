from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.executive_scorecard_service import ExecutiveScorecardService
from src.services.executive_scorecard_snapshot_service import ExecutiveScorecardSnapshotService

router = APIRouter(prefix="/api/v1/executive-scorecard", tags=["Executive Scorecard F04.7"])

_service = ExecutiveScorecardService()
_snapshot = ExecutiveScorecardSnapshotService(_service)


@router.get("/cockpit")
async def scorecard_cockpit(
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
        "decisaoArquitetural": payload.get("decisaoArquitetural"),
        "qa": payload.get("qa"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def scorecard_summary(
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
            "decisaoArquitetural": payload.get("decisaoArquitetural"),
        },
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/refresh")
async def scorecard_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
