"""Rotas de síntese executiva — Sprint 44."""

from fastapi import APIRouter, Depends, Query

from src.interfaces.http.authz import require_roles
from src.services.executive_synthesis_service import ExecutiveSynthesisService
from src.services.complete_departmental_dre_service import CompleteDepartmentalDreService
from src.services.expense_pending_service import ExpensePendingService
from src.services.departmental_alert_service import DepartmentalAlertService

router = APIRouter(
    prefix="/api/v1/executive-synthesis",
    tags=["Executive Synthesis"],
)


def _get_synthesis_service() -> ExecutiveSynthesisService:
    from src.services.director_financial_reconciliation_pipeline import (
        DirectorFinancialReconciliationPipeline,
    )
    from src.services.fuel_snapshot_service import FuelSnapshotService
    from src.services.fuel_analytics_service import FuelAnalyticsService
    from src.services.fuel_kpi_engine import FuelKpiEngine
    from src.gateway.shared_client import get_webposto_client

    client = get_webposto_client()
    reconciliation = DirectorFinancialReconciliationPipeline(client)
    fuel_analytics = FuelAnalyticsService(client)
    fuel_kpi_engine = FuelKpiEngine()
    fuel = FuelSnapshotService(fuel_analytics, fuel_kpi_engine)
    dre = CompleteDepartmentalDreService(
        reconciliation=reconciliation, fuel=fuel, non_fuel=fuel
    )
    alerts = DepartmentalAlertService()
    pending = ExpensePendingService()

    return ExecutiveSynthesisService(
        dre_service=dre,
        fuel_service=fuel,
        alert_service=alerts,
        pending_service=pending,
    )


@router.get("/dashboard")
async def executive_dashboard(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    forceRefresh: bool = Query(False),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    service = _get_synthesis_service()
    synthesis = await service.build(
        dataInicial, dataFinal, empresaCodigo, force_refresh=forceRefresh
    )
    return {
        "success": True,
        "data": synthesis.model_dump(),
        "error": None,
    }


@router.get("/fuel-margin")
async def fuel_margin_summary(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    service = _get_synthesis_service()
    synthesis = await service.build(dataInicial, dataFinal, empresaCodigo)
    return {
        "success": True,
        "data": {
            "period": {"start": dataInicial, "end": dataFinal},
            "fuelRevenue": synthesis.fuel_revenue,
            "fuelMarginPerLiter": synthesis.fuel_margin_per_liter,
            "fuelLitersSold": synthesis.fuel_liters_sold,
            "cacheHit": synthesis.cache_hit,
        },
        "error": None,
    }


@router.get("/pending-expenses")
async def pending_expenses_summary(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    pending_service = ExpensePendingService()
    summary = pending_service.group_pending_expenses([])
    return {
        "success": True,
        "data": summary.model_dump(),
        "error": None,
    }


@router.get("/alerts-critical")
async def critical_alerts(
    data: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    alerts = DepartmentalAlertService()
    all_alerts = alerts.list(data)
    critical = [a for a in all_alerts if a.get("severity") == "CRITICAL"]
    cash_related = [a for a in all_alerts if "caixa" in (a.get("type") or "").lower()]
    return {
        "success": True,
        "data": {
            "critical": critical[:10],
            "cashRelated": cash_related[:5],
            "totalAlerts": len(all_alerts),
        },
        "error": None,
    }
