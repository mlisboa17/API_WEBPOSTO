from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.nfce_intelligence_service import NfceIntelligenceService
from src.services.nfce_intelligence_snapshot_service import NfceIntelligenceSnapshotService

router = APIRouter(prefix="/api/v1/nfce-intelligence", tags=["NFCE Intelligence F06.1"])

_service = NfceIntelligenceService()
_snapshot = NfceIntelligenceSnapshotService(_service)


@router.get("/cockpit")
async def nfce_intelligence_cockpit(
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
        "nfceCatalogEngine": payload.get("nfceCatalogEngine"),
        "nfceReconciliationEngine": payload.get("nfceReconciliationEngine"),
        "nfceRiskEngine": payload.get("nfceRiskEngine"),
        "nfceAnomalyEngine": payload.get("nfceAnomalyEngine"),
        "nfceExecutiveIntelligence": payload.get("nfceExecutiveIntelligence"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def nfce_intelligence_summary(
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
            "nfceLineageEngine": payload.get("nfceLineageEngine"),
            "dwLayer": payload.get("dwLayer"),
        },
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/refresh")
async def nfce_intelligence_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
