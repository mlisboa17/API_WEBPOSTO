from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.operator_accountability_incentive_service import OperatorAccountabilityIncentiveService
from src.services.operator_accountability_incentive_snapshot_service import (
    OperatorAccountabilityIncentiveSnapshotService,
)

router = APIRouter(prefix="/api/v1/people-intelligence", tags=["People Intelligence F04.1"])

_service = OperatorAccountabilityIncentiveService()
_snapshot = OperatorAccountabilityIncentiveSnapshotService(_service)


@router.get("/snapshot")
async def people_snapshot(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None, "error": "Falha ao consolidar people intelligence"}
    return {
        "success": True,
        "data": payload,
        "snapshot": {"hit": hit, "stale": stale},
        "error": None,
    }


@router.post("/refresh")
async def people_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}


@router.get("/cockpit")
async def people_cockpit(
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


@router.get("/summary")
async def people_summary(
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
            "operatorClassification": payload.get("operatorClassification", {}).get("summary"),
        },
        "snapshot": {"hit": hit, "stale": stale},
    }
