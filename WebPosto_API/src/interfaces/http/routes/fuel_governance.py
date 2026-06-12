from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.fuel_governance_service import FuelGovernanceService
from src.services.fuel_governance_snapshot_service import FuelGovernanceSnapshotService

router = APIRouter(prefix="/api/v1/fuel-governance", tags=["Fuel Governance F06.5"])

_service = FuelGovernanceService()
_snapshot = FuelGovernanceSnapshotService(_service)


@router.get("/cockpit")
async def fuel_governance_cockpit(
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
        "lmcComplianceAudit": payload.get("lmcComplianceAudit"),
        "routineAdherenceAudit": payload.get("routineAdherenceAudit"),
        "operationalDisciplineAudit": payload.get("operationalDisciplineAudit"),
        "delayAnalysisEngine": payload.get("delayAnalysisEngine"),
        "branchComplianceRanking": payload.get("branchComplianceRanking"),
        "fuelGovernanceIntelligence": payload.get("fuelGovernanceIntelligence"),
        "processoOperacionalSuficiente": payload.get("processoOperacionalSuficiente"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def fuel_governance_summary(
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
            "fuelGovernanceIntelligence": payload.get("fuelGovernanceIntelligence"),
            "dwLayer": payload.get("dwLayer"),
        },
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/refresh")
async def fuel_governance_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
