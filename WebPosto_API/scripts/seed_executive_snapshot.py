"""Gera snapshot executivo via servico (evidencia API normal)."""
from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta

from src.gateway.webposto_client import WebPostoClient
from src.services.analytics_service import AnalyticsService
from src.services.data_quality_service import DataQualityService
from src.services.executive_snapshot_service import ExecutiveSnapshotService
from src.services.fuel_analytics_service import FuelAnalyticsService
from src.services.fuel_kpi_engine import FuelKpiEngine
from src.services.network_financial_overview_service import NetworkFinancialOverviewService


async def main() -> None:
    client = WebPostoClient()
    overview = NetworkFinancialOverviewService(client)
    service = ExecutiveSnapshotService(
        overview,
        AnalyticsService(overview),
        DataQualityService(overview),
        FuelAnalyticsService(client),
        FuelKpiEngine(),
    )

    end = date.today()
    start = end - timedelta(days=5)
    result = await service.refresh(start.isoformat(), end.isoformat())
    snapshot = service.get_snapshot(start.isoformat(), end.isoformat())
    print(json.dumps({"refresh": result, "snapshotMeta": {
        "fromSnapshot": snapshot.get("fromSnapshot"),
        "lastUpdated": snapshot.get("lastUpdated"),
        "hasKpis": bool(snapshot.get("kpis")),
        "hasDre": bool(snapshot.get("dre")),
        "hasCoverage": bool(snapshot.get("coverage")),
        "hasDataQuality": bool(snapshot.get("dataQuality")),
        "hasFuel": bool(snapshot.get("fuel")),
        "warnings": snapshot.get("warnings"),
    }}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
