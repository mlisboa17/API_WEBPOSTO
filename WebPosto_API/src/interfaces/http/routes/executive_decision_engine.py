from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.executive_decision_engine_service import ExecutiveDecisionEngineService
from src.services.executive_decision_engine_snapshot_service import ExecutiveDecisionEngineSnapshotService

router = APIRouter(prefix="/api/v1/executive-decision", tags=["Executive Decision Engine F05.1"])

_service = ExecutiveDecisionEngineService()
_snapshot = ExecutiveDecisionEngineSnapshotService(_service)


@router.get("/cockpit")
async def executive_decision_cockpit(
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
        "planoCorporativoConsolidado": payload.get("planoCorporativoConsolidado"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def executive_decision_summary(
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
            "roiPrioritizationEngine": payload.get("roiPrioritizationEngine"),
        },
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/refresh")
async def executive_decision_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
