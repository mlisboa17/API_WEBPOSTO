from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.lmc_intelligence_service import LmcIntelligenceService
from src.services.lmc_intelligence_snapshot_service import LmcIntelligenceSnapshotService

router = APIRouter(prefix="/api/v1/lmc-intelligence", tags=["LMC Intelligence F06.2"])

_service = LmcIntelligenceService()
_snapshot = LmcIntelligenceSnapshotService(_service)


@router.get("/cockpit")
async def lmc_intelligence_cockpit(
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
        "lmcCatalogEngine": payload.get("lmcCatalogEngine"),
        "fuelReconciliationEngine": payload.get("fuelReconciliationEngine"),
        "lossSurplusEngine": payload.get("lossSurplusEngine"),
        "tankIntelligence": payload.get("tankIntelligence"),
        "pumpIntelligence": payload.get("pumpIntelligence"),
        "lmcExecutiveIntelligence": payload.get("lmcExecutiveIntelligence"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def lmc_intelligence_summary(
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
async def lmc_intelligence_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
