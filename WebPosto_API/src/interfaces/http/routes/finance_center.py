from __future__ import annotations

from fastapi import APIRouter, Query

from src.gateway.webposto_client import WebPostoClient
from src.services.analytics_multiselect import build_finance_center_filters
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.finance_center_snapshot_service import FinanceCenterSnapshotService
from src.services.network_financial_overview_service import NetworkFinancialOverviewService

router = APIRouter(prefix="/api/v1/finance/center", tags=["Finance Center"])

_client = WebPostoClient()
_overview = NetworkFinancialOverviewService(_client)
_finance_center = CorporateFinanceCenterService(_overview)
_snapshot = FinanceCenterSnapshotService(_finance_center)


def _common_params(
    dataInicial: str,
    dataFinal: str,
    empresaCodigo: str | None,
    centroCusto: str | None,
    planoConta: str | None,
    categoriaLogos: str | None,
):
    return build_finance_center_filters(
        dataInicial,
        dataFinal,
        empresaCodigo,
        centro_custo=centroCusto,
        plano_conta=planoConta,
        categoria_logos=categoriaLogos,
    )


@router.get("/summary")
async def finance_center_summary(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    filters = build_finance_center_filters(dataInicial, dataFinal, empresaCodigo)
    return (await _finance_center.get_summary(filters, empresaCodigo)).to_dict()


@router.get("/expenses")
async def finance_center_expenses(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
    centroCusto: str | None = Query(None),
    planoConta: str | None = Query(None),
    categoriaLogos: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    filters = _common_params(dataInicial, dataFinal, empresaCodigo, centroCusto, planoConta, categoriaLogos)
    return (await _finance_center.get_expenses(filters, empresaCodigo, page, limit)).to_dict()


@router.get("/payables")
async def finance_center_payables(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    filters = build_finance_center_filters(dataInicial, dataFinal, empresaCodigo)
    return (await _finance_center.get_payables(filters, empresaCodigo, page, limit)).to_dict()


@router.get("/receivables")
async def finance_center_receivables(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    filters = build_finance_center_filters(dataInicial, dataFinal, empresaCodigo)
    return (await _finance_center.get_receivables(filters, empresaCodigo, page, limit)).to_dict()


@router.get("/bank-movements")
async def finance_center_bank_movements(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    filters = build_finance_center_filters(dataInicial, dataFinal, empresaCodigo)
    return (await _finance_center.get_bank_movements(filters, empresaCodigo, page, limit)).to_dict()


@router.get("/cash")
async def finance_center_cash(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    filters = build_finance_center_filters(dataInicial, dataFinal, empresaCodigo)
    return (await _finance_center.get_cash(filters, empresaCodigo)).to_dict()


@router.get("/snapshot")
async def finance_center_snapshot(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    return {"success": True, "data": _snapshot.get_snapshot(dataInicial, dataFinal, empresaCodigo), "error": None}


@router.post("/refresh")
async def finance_center_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    import asyncio

    asyncio.create_task(_snapshot.refresh_background(dataInicial, dataFinal, empresaCodigo))
    return {"success": True, "data": {"status": "refresh_started"}, "error": None}
