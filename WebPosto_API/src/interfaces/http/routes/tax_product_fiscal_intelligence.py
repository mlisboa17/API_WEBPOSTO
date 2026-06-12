from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.tax_product_fiscal_intelligence_service import TaxProductFiscalIntelligenceService
from src.services.tax_product_fiscal_intelligence_snapshot_service import TaxProductFiscalIntelligenceSnapshotService

router = APIRouter(prefix="/api/v1/fiscal-intelligence", tags=["Fiscal Intelligence F06.3"])

_service = TaxProductFiscalIntelligenceService()
_snapshot = TaxProductFiscalIntelligenceSnapshotService(_service)


@router.get("/cockpit")
async def fiscal_intelligence_cockpit(
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
        "productFiscalCatalogEngine": payload.get("productFiscalCatalogEngine"),
        "ncmIntelligenceEngine": payload.get("ncmIntelligenceEngine"),
        "taxClassificationEngine": payload.get("taxClassificationEngine"),
        "financialClassificationEngine": payload.get("financialClassificationEngine"),
        "fiscalRiskEngine": payload.get("fiscalRiskEngine"),
        "executiveFiscalIntelligence": payload.get("executiveFiscalIntelligence"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def fiscal_intelligence_summary(
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
async def fiscal_intelligence_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
