from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.non_fuel_product_sales_snapshot_service import NonFuelProductSalesSnapshotService
from src.services.commercial_action_center_service import CommercialActionCenterService

router = APIRouter(prefix="/api/v1/non-fuel-products", tags=["Produtos Vendidos F07.6"])

_service = CommercialActionCenterService()
_snapshot = NonFuelProductSalesSnapshotService(_service)


@router.get("/cockpit")
async def non_fuel_products_cockpit(
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
        "multiTenantScalabilityEngine": payload.get("multiTenantScalabilityEngine"),
        "productMasterCoverage": payload.get("productMasterCoverage"),
        "productMatchRecovery": payload.get("productMatchRecovery"),
        "residualSkuForensics": payload.get("residualSkuForensics"),
        "productLookupOptimization": payload.get("productLookupOptimization"),
        "productCacheStrategy": payload.get("productCacheStrategy"),
        "departmentRefinement": payload.get("departmentRefinement"),
        "multiBranchProductScale": payload.get("multiBranchProductScale"),
        "opportunityEngine": payload.get("opportunityEngine"),
        "productSalesPerformance": payload.get("productSalesPerformance"),
        "marginIntelligence": payload.get("marginIntelligence"),
        "mixHealthCommercial": payload.get("mixHealthCommercial"),
        "productOpportunityAssortment": payload.get("productOpportunityAssortment"),
        "assortmentIntelligence": payload.get("assortmentIntelligence"),
        "commercialActionCenter": payload.get("commercialActionCenter"),
        "productPerformanceBenchmark": payload.get("productPerformanceBenchmark"),
        "departmentIntelligence": payload.get("departmentIntelligence"),
        "productRevenueIntelligence": payload.get("productRevenueIntelligence"),
        "branchProductMix": payload.get("branchProductMix"),
        "nonFuelSalesEngine": payload.get("nonFuelSalesEngine"),
        "productRankingEngine": payload.get("productRankingEngine"),
        "branchDepartmentAnalytics": payload.get("branchDepartmentAnalytics"),
        "productSalesLineage": payload.get("productSalesLineage"),
        "salesCoverageReconciliation": payload.get("salesCoverageReconciliation"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/summary")
async def non_fuel_products_summary(
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
            "productSalesLineage": payload.get("productSalesLineage"),
            "dwLayer": payload.get("dwLayer"),
        },
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.post("/refresh")
async def non_fuel_products_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _snapshot.collect(dataInicial, dataFinal, empresaCodigo)
    return {"success": result.get("status") == "ok", "data": result}
