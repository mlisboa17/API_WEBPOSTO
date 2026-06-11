from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.corporate_intelligence_hub_service import CorporateIntelligenceHubService
from src.services.corporate_intelligence_hub_snapshot_service import CorporateIntelligenceHubSnapshotService

router = APIRouter(prefix="/api/v1/corporate-hub", tags=["Corporate Intelligence Hub F05.0"])

_service = CorporateIntelligenceHubService()
_snapshot = CorporateIntelligenceHubSnapshotService(_service)


@router.get("/cockpit")
async def corporate_hub_cockpit(
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
async def corporate_hub_summary(
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
async def corporate_hub_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
