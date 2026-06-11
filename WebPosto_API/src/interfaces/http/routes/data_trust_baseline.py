from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.live_data_truth_baseline_service import LiveDataTruthBaselineService
from src.services.live_data_truth_baseline_snapshot_service import LiveDataTruthBaselineSnapshotService
from src.services.coverage_truth_audit_service import CoverageTruthAuditService
from src.services.coverage_truth_audit_snapshot_service import CoverageTruthAuditSnapshotService
from src.services.executive_coverage_recovery_service import ExecutiveCoverageRecoveryService
from src.services.executive_coverage_recovery_snapshot_service import ExecutiveCoverageRecoverySnapshotService

router = APIRouter(prefix="/api/v1/data-trust", tags=["Data Trust D04"])

_service = LiveDataTruthBaselineService()
_snapshot = LiveDataTruthBaselineSnapshotService(_service)
_challenge = CoverageTruthAuditService()
_challenge_snapshot = CoverageTruthAuditSnapshotService(_challenge)
_recovery = ExecutiveCoverageRecoveryService()
_recovery_snapshot = ExecutiveCoverageRecoverySnapshotService(_recovery)


@router.get("/baseline")
async def data_trust_baseline(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None}
    return {
        "success": True,
        "data": payload,
        "executiveAnswers": payload.get("executiveAnswers"),
        "parecerFinal": payload.get("parecerFinal"),
        "dataGovernance": payload.get("dataGovernance"),
        "qaCertification": payload.get("qaCertification"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/refresh")
async def data_trust_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}


@router.get("/coverage-challenge")
async def data_trust_coverage_challenge(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _challenge_snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None}
    return {
        "success": True,
        "data": payload,
        "executiveAnswers": payload.get("executiveAnswers"),
        "parecerFinal": payload.get("parecerFinal"),
        "trustScoreChallenge": payload.get("trustScoreChallenge"),
        "qaCertification": payload.get("qaCertification"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/coverage-challenge/refresh")
async def data_trust_coverage_challenge_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _challenge_snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}


@router.get("/executive-recovery")
async def data_trust_executive_recovery(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _recovery_snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None}
    return {
        "success": True,
        "data": payload,
        "executiveAnswers": payload.get("executiveAnswers"),
        "parecerFinal": payload.get("parecerFinal"),
        "executiveCoverageRecalculation": payload.get("executiveCoverageRecalculation"),
        "executiveTrustGovernance": payload.get("executiveTrustGovernance"),
        "qaCertification": payload.get("qaCertification"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/executive-recovery/refresh")
async def data_trust_executive_recovery_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _recovery_snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
