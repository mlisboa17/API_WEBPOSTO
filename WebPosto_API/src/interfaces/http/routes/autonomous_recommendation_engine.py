from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.autonomous_recommendation_engine_service import AutonomousRecommendationEngineService
from src.services.autonomous_recommendation_engine_snapshot_service import (
    AutonomousRecommendationEngineSnapshotService,
)

router = APIRouter(prefix="/api/v1/autonomous-recommendations", tags=["Autonomous Recommendation F05.4"])

_service = AutonomousRecommendationEngineService()
_snapshot = AutonomousRecommendationEngineSnapshotService(_service)


@router.get("/cockpit")
async def autonomous_recommendations_cockpit(
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
        "executiveFeedEngine": payload.get("executiveFeedEngine"),
        "recommendationPrioritizationEngine": payload.get("recommendationPrioritizationEngine"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def autonomous_recommendations_summary(
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
            "opportunityDiscoveryEngine": payload.get("opportunityDiscoveryEngine"),
            "riskDiscoveryEngine": payload.get("riskDiscoveryEngine"),
        },
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/refresh")
async def autonomous_recommendations_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
