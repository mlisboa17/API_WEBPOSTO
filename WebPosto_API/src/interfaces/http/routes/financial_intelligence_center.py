"""F08.4 — API read-only do Financial Intelligence Center."""
from __future__ import annotations

from fastapi import APIRouter, Query

from src.services.financial_intelligence_center_service import get_financial_intelligence_center

router = APIRouter(prefix="/api/v1/financial/intelligence-center", tags=["Financial Intelligence Center F08.4"])

_center = get_financial_intelligence_center()


@router.get("/cockpit")
async def intelligence_cockpit(
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    empresaCodigo: str | None = Query(None),
) -> dict:
    data = _center.get_cockpit(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": data, "error": None}


@router.get("/trends")
async def intelligence_trends(
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    empresaCodigo: str | None = Query(None),
) -> dict:
    data = _center.get_trends(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": data, "error": None}


@router.get("/risks")
async def intelligence_risks(
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    empresaCodigo: str | None = Query(None),
) -> dict:
    data = _center.get_risks(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": data, "error": None}


@router.get("/opportunities")
async def intelligence_opportunities(
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    empresaCodigo: str | None = Query(None),
) -> dict:
    data = _center.get_opportunities(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": data, "error": None}


@router.get("/dw-export")
async def intelligence_dw_export(
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    empresaCodigo: str | None = Query(None),
) -> dict:
    row = _center.dw_row(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": {"rows": [row], "total": 1}, "error": None}
