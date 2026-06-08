from __future__ import annotations

from fastapi import APIRouter, Query

from src.gateway.webposto_client import WebPostoClient
from src.services.analytics_multiselect import build_finance_center_filters
from src.services.cash_flow_snapshot_service import CashFlowSnapshotService
from src.services.corporate_cash_flow_service import CorporateCashFlowService
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.network_financial_overview_service import NetworkFinancialOverviewService

router = APIRouter(prefix="/api/v1/finance/cash-flow", tags=["Cash Flow"])

_client = WebPostoClient()
_overview = NetworkFinancialOverviewService(_client)
_finance_center = CorporateFinanceCenterService(_overview)
_cash_flow = CorporateCashFlowService(_finance_center)
_snapshot = CashFlowSnapshotService(_cash_flow)


@router.get("")
async def cash_flow_all(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    filters = build_finance_center_filters(dataInicial, dataFinal, empresaCodigo)
    return (await _cash_flow.build(filters, empresaCodigo)).to_dict()


@router.get("/daily")
async def cash_flow_daily(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    resp = await cash_flow_all(dataInicial, dataFinal, empresaCodigo)
    data = resp.get("data") or {}
    return {"success": resp.get("success"), "data": data.get("daily"), "error": resp.get("error")}


@router.get("/weekly")
async def cash_flow_weekly(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    resp = await cash_flow_all(dataInicial, dataFinal, empresaCodigo)
    data = resp.get("data") or {}
    return {"success": resp.get("success"), "data": data.get("weekly"), "error": resp.get("error")}


@router.get("/monthly")
async def cash_flow_monthly(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    resp = await cash_flow_all(dataInicial, dataFinal, empresaCodigo)
    data = resp.get("data") or {}
    return {"success": resp.get("success"), "data": data.get("monthly"), "error": resp.get("error")}


@router.get("/snapshot")
async def cash_flow_snapshot(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    return {"success": True, "data": _snapshot.get_snapshot(dataInicial, dataFinal, empresaCodigo), "error": None}


@router.post("/refresh")
async def cash_flow_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    import asyncio

    asyncio.create_task(_snapshot.refresh_background(dataInicial, dataFinal, empresaCodigo))
    return {"success": True, "data": {"status": "refresh_started"}, "error": None}
