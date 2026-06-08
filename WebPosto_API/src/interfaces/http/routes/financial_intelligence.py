from __future__ import annotations

from fastapi import APIRouter, Query

from src.gateway.webposto_client import WebPostoClient
from src.services.analytics_multiselect import build_finance_center_filters
from src.services.corporate_cash_flow_service import CorporateCashFlowService
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.finance_intelligence_snapshot_service import FinanceIntelligenceSnapshotService
from src.services.financial_health_score_service import FinancialHealthScoreService
from src.services.financial_health_score_v3_service import FinancialHealthScoreV3Service
from src.services.financial_intelligence_advanced_service import FinancialIntelligenceAdvancedService
from src.services.financial_intelligence_service import FinancialIntelligenceService
from src.services.network_financial_overview_service import NetworkFinancialOverviewService
from src.services.supplier_intelligence_service import SupplierIntelligenceService
from src.services.supplier_segmentation_service import SupplierSegmentationService

router = APIRouter(prefix="/api/v1/finance/intelligence", tags=["Financial Intelligence"])

_client = WebPostoClient()
_overview = NetworkFinancialOverviewService(_client)
_finance_center = CorporateFinanceCenterService(_overview)
_cash_flow = CorporateCashFlowService(_finance_center)
_intelligence = FinancialIntelligenceService(_finance_center, _cash_flow)
_advanced = FinancialIntelligenceAdvancedService(_finance_center)
_health = FinancialHealthScoreService(_finance_center, _cash_flow, _intelligence)
_health_v3 = FinancialHealthScoreV3Service(_finance_center, _advanced)
_suppliers = SupplierIntelligenceService(_finance_center)
_segmentation = SupplierSegmentationService(_finance_center)
_snapshot = FinanceIntelligenceSnapshotService(_intelligence, _health, _advanced, _health_v3, _suppliers, _segmentation)


@router.get("")
async def financial_intelligence(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    filters = build_finance_center_filters(dataInicial, dataFinal, empresaCodigo)
    return (await _intelligence.build(filters, empresaCodigo)).to_dict()


@router.get("/health-score")
async def financial_health_score(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    filters = build_finance_center_filters(dataInicial, dataFinal, empresaCodigo)
    return (await _health.build(filters, empresaCodigo)).to_dict()


@router.get("/advanced")
async def financial_intelligence_advanced(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    filters = build_finance_center_filters(dataInicial, dataFinal, empresaCodigo)
    return (await _advanced.build(filters, empresaCodigo)).to_dict()


@router.get("/health-score-v3")
async def financial_health_score_v3(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    filters = build_finance_center_filters(dataInicial, dataFinal, empresaCodigo)
    return (await _health_v3.build(filters, empresaCodigo)).to_dict()


@router.get("/segmentation")
async def financial_supplier_segmentation(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    filters = build_finance_center_filters(dataInicial, dataFinal, empresaCodigo)
    return (await _segmentation.build(filters, empresaCodigo)).to_dict()


@router.get("/suppliers")
async def financial_supplier_intelligence(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    filters = build_finance_center_filters(dataInicial, dataFinal, empresaCodigo)
    return (await _suppliers.build(filters, empresaCodigo)).to_dict()


@router.get("/snapshot")
async def financial_intelligence_snapshot(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    return {"success": True, "data": _snapshot.get_snapshot(dataInicial, dataFinal, empresaCodigo), "error": None}


@router.post("/refresh")
async def financial_intelligence_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    import asyncio

    asyncio.create_task(_snapshot.refresh_background(dataInicial, dataFinal, empresaCodigo))
    return {"success": True, "data": {"status": "refresh_started"}, "error": None}
