from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Query

from src.gateway.webposto_client import WebPostoClient
from src.services.analytics_multiselect import (
    build_overview_filters,
    fetch_data_quality_multiselect,
    fetch_dre_multiselect,
    fetch_fuel_executive_multiselect,
    fetch_fuel_summary_multiselect,
    fetch_kpis_multiselect,
)
from src.services.analytics_service import AnalyticsService
from src.services.data_quality_service import DataQualityService
from src.services.financial_operational_snapshot_service import FinancialOperationalSnapshotService
from src.services.fuel_analytics_service import FuelAnalyticsService
from src.services.fuel_kpi_engine import FuelKpiEngine
from src.services.fuel_snapshot_service import FuelSnapshotService
from src.services.multiselect_utils import empresa_codigo_cache_key
from src.services.network_financial_overview_service import NetworkFinancialOverviewService
from src.services.produto_catalog import ProdutoCatalogService
from src.services.sync_control_service import integration_log_service, sync_control_service
from src.services.analytics_cache import build_cache_key, get_cache, set_cache
from src.services.executive_snapshot_service import ExecutiveSnapshotService, build_network_coverage

router = APIRouter(prefix="/api/v1", tags=["LOGOS SPACE Analytics"])

_client = WebPostoClient()
_overview = NetworkFinancialOverviewService(_client)
_analytics = AnalyticsService(_overview)
_data_quality = DataQualityService(_overview)
_fuel_analytics = FuelAnalyticsService(_client)
_fuel_kpi_engine = FuelKpiEngine()
_product_catalog = ProdutoCatalogService(_client)
_executive_snapshot = ExecutiveSnapshotService(
    _overview,
    _analytics,
    _data_quality,
    _fuel_analytics,
    _fuel_kpi_engine,
)
_fuel_snapshot = FuelSnapshotService(_fuel_analytics, _fuel_kpi_engine)
_financial_snapshot = FinancialOperationalSnapshotService(_overview)


@router.get("/kpis")
async def get_kpis(
    dataInicial: str = Query(..., description="Data inicial YYYY-MM-DD"),
    dataFinal: str = Query(..., description="Data final YYYY-MM-DD"),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
    centroCusto: str | None = Query(None),
    tipoDespesa: str | None = Query(None),
) -> dict:
    cache_params = {
        "data_inicial": dataInicial,
        "data_final": dataFinal,
        "empresa_codigo": empresa_codigo_cache_key(empresaCodigo),
        "filial": None,
    }
    key = build_cache_key("kpis", cache_params)
    hit = get_cache(key)
    if hit is not None:
        return hit

    res_dict = await fetch_kpis_multiselect(
        _analytics, dataInicial, dataFinal, empresaCodigo, centroCusto, tipoDespesa
    )
    set_cache(key, res_dict, ttl=60.0)
    return res_dict


@router.get("/sales/fuel-summary")
async def get_sales_fuel_summary(
    dataInicial: str = Query(..., description="Data inicial YYYY-MM-DD"),
    dataFinal: str = Query(..., description="Data final YYYY-MM-DD"),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
    filial: str | None = Query(None),
    combustivel: str | None = Query(None),
) -> list[dict]:
    cache_params = {
        "data_inicial": dataInicial,
        "data_final": dataFinal,
        "empresa_codigo": empresa_codigo_cache_key(empresaCodigo),
        "filial": filial,
        "combustivel": combustivel,
    }
    key = build_cache_key("fuel-summary", cache_params)
    hit = get_cache(key)
    if hit is not None:
        return hit

    res_list = await fetch_fuel_summary_multiselect(
        _analytics, dataInicial, dataFinal, empresaCodigo, combustivel, filial
    )
    set_cache(key, res_list, ttl=60.0)
    return res_list


@router.get("/fuel/executive")
async def get_fuel_executive(
    dataInicial: str = Query(..., description="Data inicial YYYY-MM-DD"),
    dataFinal: str = Query(..., description="Data final YYYY-MM-DD"),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
) -> dict:
    cache_params = {
        "data_inicial": dataInicial,
        "data_final": dataFinal,
        "empresa_codigo": empresa_codigo_cache_key(empresaCodigo),
    }
    key = build_cache_key("fuel-executive", cache_params)
    hit = get_cache(key)
    if hit is not None:
        return hit

    response = await fetch_fuel_executive_multiselect(
        _fuel_analytics, _fuel_kpi_engine, dataInicial, dataFinal, empresaCodigo
    )
    set_cache(key, response, ttl=900.0)
    return response


@router.get("/products/catalog")
async def get_products_catalog(
    empresaCodigo: str | None = Query(None, description="Lista de empresas separadas por virgula"),
) -> dict:
    company_codes: list[int] = []
    if empresaCodigo:
        for chunk in empresaCodigo.split(","):
            value = chunk.strip()
            if value.isdigit():
                company_codes.append(int(value))

    resp = await _product_catalog.get_catalog(company_codes or None)
    return resp.to_dict()


@router.get("/dre")
async def get_dre(
    dataInicial: str = Query(..., description="Data inicial YYYY-MM-DD"),
    dataFinal: str = Query(..., description="Data final YYYY-MM-DD"),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
    centroCusto: str | None = Query(None),
) -> dict:
    cache_params = {
        "data_inicial": dataInicial,
        "data_final": dataFinal,
        "empresa_codigo": empresa_codigo_cache_key(empresaCodigo),
        "filial": None,
    }
    key = build_cache_key("dre", cache_params)
    hit = get_cache(key)
    if hit is not None:
        return hit

    res_dict = await fetch_dre_multiselect(_analytics, dataInicial, dataFinal, empresaCodigo, centroCusto)
    set_cache(key, res_dict, ttl=60.0)
    return res_dict


@router.get("/data-quality")
async def get_data_quality(
    dataInicial: str = Query(..., description="Data inicial YYYY-MM-DD"),
    dataFinal: str = Query(..., description="Data final YYYY-MM-DD"),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
    filial: str | None = Query(None),
    centroCusto: str | None = Query(None),
    tipoProduto: str | None = Query(None),
    grupoProduto: str | None = Query(None),
) -> dict:
    cache_params = {
        "data_inicial": dataInicial,
        "data_final": dataFinal,
        "empresa_codigo": empresa_codigo_cache_key(empresaCodigo),
        "filial": filial,
    }
    key = build_cache_key("data-quality", cache_params)
    hit = get_cache(key)
    if hit is not None:
        return hit

    res_dict = await fetch_data_quality_multiselect(
        _data_quality,
        dataInicial,
        dataFinal,
        empresaCodigo,
        filial,
        centroCusto,
        tipoProduto,
        grupoProduto,
    )
    set_cache(key, res_dict, ttl=60.0)
    return res_dict


@router.get("/filiais")
async def get_filiais() -> dict:
    resp = await _overview.get_companies()
    return resp.to_dict()


@router.get("/network/coverage")
async def get_network_coverage() -> dict:
    resp = await _overview.get_companies()
    companies = resp.data["data"] if resp.success and resp.data else []
    return build_network_coverage(companies)


@router.get("/executive/snapshot")
async def get_executive_snapshot(
    dataInicial: str = Query(..., description="Data inicial YYYY-MM-DD"),
    dataFinal: str = Query(..., description="Data final YYYY-MM-DD"),
    empresaCodigo: str | None = Query(None, description="Codigo da empresa ou lista separada por virgula"),
    centroCusto: str | None = Query(None),
    tipoDespesa: str | None = Query(None),
) -> dict:
    _ = centroCusto, tipoDespesa
    return _executive_snapshot.get_snapshot(dataInicial, dataFinal, empresaCodigo)


@router.post("/executive/refresh")
async def post_executive_refresh(
    dataInicial: str = Query(..., description="Data inicial YYYY-MM-DD"),
    dataFinal: str = Query(..., description="Data final YYYY-MM-DD"),
    empresaCodigo: str | None = Query(None, description="Codigo da empresa ou lista separada por virgula"),
    centroCusto: str | None = Query(None),
    tipoDespesa: str | None = Query(None),
) -> dict:
    return _executive_snapshot.start_refresh_background(
        dataInicial,
        dataFinal,
        empresaCodigo,
        centroCusto,
        tipoDespesa,
    )


@router.get("/fuel/snapshot")
async def get_fuel_snapshot(
    dataInicial: str = Query(..., description="Data inicial YYYY-MM-DD"),
    dataFinal: str = Query(..., description="Data final YYYY-MM-DD"),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
) -> dict:
    return _fuel_snapshot.get_snapshot(dataInicial, dataFinal, empresaCodigo)


@router.post("/fuel/refresh")
async def post_fuel_refresh(
    dataInicial: str = Query(..., description="Data inicial YYYY-MM-DD"),
    dataFinal: str = Query(..., description="Data final YYYY-MM-DD"),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
) -> dict:
    return _fuel_snapshot.start_refresh_background(dataInicial, dataFinal, empresaCodigo)


@router.get("/financial/snapshot")
async def get_financial_snapshot(
    dataInicial: str = Query(..., description="Data inicial YYYY-MM-DD"),
    dataFinal: str = Query(..., description="Data final YYYY-MM-DD"),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
    centroCusto: str | None = Query(None),
    tipoDespesa: str | None = Query(None),
) -> dict:
    return _financial_snapshot.get_snapshot(
        dataInicial, dataFinal, empresaCodigo, centroCusto, tipoDespesa
    )


@router.post("/financial/refresh")
async def post_financial_refresh(
    dataInicial: str = Query(..., description="Data inicial YYYY-MM-DD"),
    dataFinal: str = Query(..., description="Data final YYYY-MM-DD"),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
    centroCusto: str | None = Query(None),
    tipoDespesa: str | None = Query(None),
) -> dict:
    return _financial_snapshot.start_refresh_background(
        dataInicial, dataFinal, empresaCodigo, centroCusto, tipoDespesa
    )


@router.get("/sync/control")
async def get_sync_control() -> dict:
    return {
        "success": True,
        "data": sync_control_service.get_all(),
        "error": None,
    }


@router.get("/sync/logs")
async def get_integration_logs(limit: int = Query(50, le=500)) -> dict:
    return {
        "success": True,
        "data": integration_log_service.list_recent(limit=limit),
        "error": None,
    }


@router.get("/sync/errors")
async def get_integration_errors(limit: int = Query(50, le=500)) -> dict:
    return {
        "success": True,
        "data": integration_log_service.list_errors(limit=limit),
        "error": None,
    }


@router.post("/sync/control/{endpoint}/reset")
async def reset_sync_control(endpoint: str) -> dict:
    sync_control_service.reset(endpoint)
    return {"success": True, "data": {"endpoint": endpoint, "reset": True}, "error": None}
