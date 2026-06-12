from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.fiscal_reconciliation_hub_service import FiscalReconciliationHubService
from src.services.fiscal_reconciliation_hub_snapshot_service import FiscalReconciliationHubSnapshotService

router = APIRouter(prefix="/api/v1/fiscal-reconciliation", tags=["Fiscal Reconciliation Hub F06.4"])

_service = FiscalReconciliationHubService()
_snapshot = FiscalReconciliationHubSnapshotService(_service)


@router.get("/cockpit")
async def fiscal_reconciliation_cockpit(
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
        "fiscalLineageEngine": payload.get("fiscalLineageEngine"),
        "nfceVendaReconciliation": payload.get("nfceVendaReconciliation"),
        "productSalesReconciliation": payload.get("productSalesReconciliation"),
        "lmcSalesReconciliation": payload.get("lmcSalesReconciliation"),
        "fiscalFinancialBridge": payload.get("fiscalFinancialBridge"),
        "fiscalRiskConsolidation": payload.get("fiscalRiskConsolidation"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def fiscal_reconciliation_summary(
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
            "fiscalLineageEngine": payload.get("fiscalLineageEngine"),
            "dwLayer": payload.get("dwLayer"),
        },
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/refresh")
async def fiscal_reconciliation_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
