from __future__ import annotations

from typing import Any

from src.services.analytics_service import AnalyticsService
from src.services.data_quality_service import DataQualityFilters, DataQualityService
from src.services.executive_snapshot_service import (
    _aggregate_data_quality,
    _aggregate_dre,
    _aggregate_kpis,
)
from src.services.fuel_aggregate import aggregate_fuel_executive_payload
from src.services.fuel_analytics_service import FuelAnalyticsFilters, FuelAnalyticsService
from src.services.fuel_kpi_engine import FuelKpiEngine
from src.services.multiselect_utils import parse_empresa_codigos
from src.services.network_financial_overview_service import FinancialOverviewFilters


def build_overview_filters(
    data_inicial: str,
    data_final: str,
    empresa_codigo: str | int | None,
    centro_custo: str | None = None,
    tipo_despesa: str | None = None,
) -> FinancialOverviewFilters:
    codes = parse_empresa_codigos(empresa_codigo)
    if len(codes) == 1:
        return FinancialOverviewFilters(
            data_inicial=data_inicial,
            data_final=data_final,
            empresa_codigo=codes[0],
            centro_custo=centro_custo,
            tipo_despesa=tipo_despesa,
        )
    if len(codes) > 1:
        return FinancialOverviewFilters(
            data_inicial=data_inicial,
            data_final=data_final,
            empresa_codigos=tuple(codes),
            centro_custo=centro_custo,
            tipo_despesa=tipo_despesa,
        )
    return FinancialOverviewFilters(
        data_inicial=data_inicial,
        data_final=data_final,
        centro_custo=centro_custo,
        tipo_despesa=tipo_despesa,
    )


def build_finance_center_filters(
    data_inicial: str,
    data_final: str,
    empresa_codigo: str | int | None,
    centro_custo: str | None = None,
    plano_conta: str | None = None,
    categoria_logos: str | None = None,
) -> FinancialOverviewFilters:
    base = build_overview_filters(data_inicial, data_final, empresa_codigo, centro_custo, None)
    return FinancialOverviewFilters(
        data_inicial=base.data_inicial,
        data_final=base.data_final,
        empresa_codigo=base.empresa_codigo,
        empresa_codigos=base.empresa_codigos,
        centro_custo=centro_custo or base.centro_custo,
        plano_conta=plano_conta,
        categoria_logos=categoria_logos,
    )


async def fetch_kpis_multiselect(
    analytics: AnalyticsService,
    data_inicial: str,
    data_final: str,
    empresa_codigo: str | int | None,
    centro_custo: str | None = None,
    tipo_despesa: str | None = None,
) -> dict[str, Any]:
    codes = parse_empresa_codigos(empresa_codigo)
    if len(codes) <= 1:
        filters = build_overview_filters(data_inicial, data_final, empresa_codigo, centro_custo, tipo_despesa)
        return (await analytics.get_kpis(filters)).to_dict()

    items: list[dict[str, Any]] = []
    for code in codes:
        filters = FinancialOverviewFilters(
            data_inicial=data_inicial,
            data_final=data_final,
            empresa_codigo=code,
            centro_custo=centro_custo,
            tipo_despesa=tipo_despesa,
        )
        resp = await analytics.get_kpis(filters)
        if resp.success and resp.data:
            items.append(resp.data)

    aggregated = _aggregate_kpis(items, data_inicial, data_final) if items else None
    return {"success": bool(items), "data": aggregated, "error": None if items else "Nenhum KPI retornado"}


async def fetch_dre_multiselect(
    analytics: AnalyticsService,
    data_inicial: str,
    data_final: str,
    empresa_codigo: str | int | None,
    centro_custo: str | None = None,
) -> dict[str, Any]:
    codes = parse_empresa_codigos(empresa_codigo)
    if len(codes) <= 1:
        filters = build_overview_filters(data_inicial, data_final, empresa_codigo, centro_custo, None)
        return (await analytics.get_dre(filters)).to_dict()

    items: list[dict[str, Any]] = []
    for code in codes:
        filters = FinancialOverviewFilters(
            data_inicial=data_inicial,
            data_final=data_final,
            empresa_codigo=code,
            centro_custo=centro_custo,
        )
        resp = await analytics.get_dre(filters)
        if resp.success and resp.data:
            items.append(resp.data)

    aggregated = _aggregate_dre(items, data_inicial, data_final) if items else None
    return {"success": bool(items), "data": aggregated, "error": None if items else "Nenhum DRE retornado"}


async def fetch_data_quality_multiselect(
    data_quality: DataQualityService,
    data_inicial: str,
    data_final: str,
    empresa_codigo: str | int | None,
    filial: str | None = None,
    centro_custo: str | None = None,
    tipo_produto: str | None = None,
    grupo_produto: str | None = None,
) -> dict[str, Any]:
    codes = parse_empresa_codigos(empresa_codigo)
    if len(codes) <= 1:
        single = codes[0] if codes else None
        dq_filters = DataQualityFilters(
            data_inicial=data_inicial,
            data_final=data_final,
            empresa_codigo=single,
            filial=filial,
            centro_custo=centro_custo,
            tipo_produto=tipo_produto,
            grupo_produto=grupo_produto,
        )
        return (await data_quality.get_data_quality(dq_filters)).to_dict()

    items: list[dict[str, Any]] = []
    for code in codes:
        dq_filters = DataQualityFilters(
            data_inicial=data_inicial,
            data_final=data_final,
            empresa_codigo=code,
            filial=filial,
            centro_custo=centro_custo,
            tipo_produto=tipo_produto,
            grupo_produto=grupo_produto,
        )
        resp = await data_quality.get_data_quality(dq_filters)
        if resp.success and resp.data:
            items.append(resp.data)

    aggregated = _aggregate_data_quality(items) if items else None
    return {"success": bool(items), "data": aggregated, "error": None if items else "Nenhum dado de qualidade"}


async def fetch_fuel_executive_multiselect(
    fuel_analytics: FuelAnalyticsService,
    fuel_kpi_engine: FuelKpiEngine,
    data_inicial: str,
    data_final: str,
    empresa_codigo: str | int | None,
) -> dict[str, Any]:
    codes = parse_empresa_codigos(empresa_codigo)
    if len(codes) <= 1:
        single = codes[0] if codes else None
        filters = FuelAnalyticsFilters(data_inicial=data_inicial, data_final=data_final, empresa_codigo=single)
        summary_resp = await fuel_analytics.get_fuel_summary(filters)
        if not summary_resp.success:
            return summary_resp.to_dict()
        payload = summary_resp.data or {}
        payload["kpis"] = fuel_kpi_engine.build(payload)
        return {"success": True, "data": payload, "error": None}

    payloads: list[dict[str, Any]] = []
    for code in codes:
        filters = FuelAnalyticsFilters(data_inicial=data_inicial, data_final=data_final, empresa_codigo=code)
        resp = await fuel_analytics.get_fuel_summary(filters)
        if resp.success and resp.data:
            payloads.append(resp.data)

    if not payloads:
        return {"success": False, "data": None, "error": "Nenhum dado de combustivel retornado"}

    merged = payloads[0]
    for extra in payloads[1:]:
        for field in ("filiais", "detalhes", "combustiveis"):
            merged.setdefault(field, [])
            merged[field] = list(merged.get(field) or []) + list(extra.get(field) or [])
        merged["litrosTotal"] = float(merged.get("litrosTotal") or 0) + float(extra.get("litrosTotal") or 0)

    merged = aggregate_fuel_executive_payload(merged, codes)
    merged["kpis"] = fuel_kpi_engine.build(merged)
    return {"success": True, "data": merged, "error": None}


async def fetch_fuel_summary_multiselect(
    analytics: AnalyticsService,
    data_inicial: str,
    data_final: str,
    empresa_codigo: str | int | None,
    combustivel_filtro: str | None = None,
    filial_filtro: str | None = None,
) -> list[dict[str, Any]]:
    codes = parse_empresa_codigos(empresa_codigo)
    if len(codes) <= 1:
        filters = build_overview_filters(data_inicial, data_final, empresa_codigo)
        resp = await analytics.get_fuel_summary(filters, combustivel_filtro=combustivel_filtro, filial_filtro=filial_filtro)
        return resp.data if resp.success and isinstance(resp.data, list) else []

    rows: list[dict[str, Any]] = []
    for code in codes:
        filters = FinancialOverviewFilters(data_inicial=data_inicial, data_final=data_final, empresa_codigo=code)
        resp = await analytics.get_fuel_summary(filters, combustivel_filtro=combustivel_filtro, filial_filtro=filial_filtro)
        if resp.success and isinstance(resp.data, list):
            rows.extend(resp.data)
    return rows
