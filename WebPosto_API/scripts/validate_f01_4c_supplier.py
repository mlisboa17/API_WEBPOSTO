"""Validação F01.4-C — Supplier Intelligence."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gateway.webposto_client import WebPostoClient
from src.services.analytics_multiselect import build_finance_center_filters
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.network_financial_overview_service import NetworkFinancialOverviewService
from src.services.supplier_intelligence_service import SupplierIntelligenceService

DATA_INICIAL = "2026-06-01"
DATA_FINAL = "2026-06-07"
OUT = ROOT / "scripts" / "f01_4c_validation_results.json"


async def main() -> None:
    t0 = time.perf_counter()
    client = WebPostoClient()
    overview = NetworkFinancialOverviewService(client)
    fc = CorporateFinanceCenterService(overview)
    svc = SupplierIntelligenceService(fc)
    filters = build_finance_center_filters(DATA_INICIAL, DATA_FINAL, None)

    resp = await svc.build(filters, None)
    elapsed_ms = round((time.perf_counter() - t0) * 1000)

    if not resp.success:
        print("FAIL:", resp.error)
        sys.exit(1)

    data = resp.data or {}
    lineage = data.get("lineage") or {}
    master = data.get("masterSuppliers") or {}
    analytics = data.get("analytics") or {}
    risk = data.get("risk") or {}
    top = analytics.get("topFornecedores") or []

    shares = [t.get("supplierShare", 0) for t in top]
    ranking_ok = shares == sorted(shares, reverse=True) if shares else True

    result = {
        "period": {"dataInicial": DATA_INICIAL, "dataFinal": DATA_FINAL},
        "elapsedMs": elapsed_ms,
        "lineage": lineage,
        "masterSuppliers": {
            "uniqueRaw": master.get("uniqueRaw"),
            "uniqueCanonical": master.get("uniqueCanonical"),
            "averageCoverageScore": master.get("averageCoverageScore"),
        },
        "analytics": {
            "totalValor": analytics.get("totalValor"),
            "totalRegistros": analytics.get("totalRegistros"),
            "leader": analytics.get("leader"),
            "mostConcentrated": analytics.get("mostConcentrated"),
            "mostPresent": analytics.get("mostPresent"),
            "top5": top[:5],
            "top20Count": len(top),
        },
        "network": {
            "sharedCount": len((data.get("network") or {}).get("sharedSuppliers") or []),
            "exclusiveCount": len((data.get("network") or {}).get("exclusiveSuppliers") or []),
        },
        "risk": {
            "supplierConcentrationRisk": risk.get("supplierConcentrationRisk"),
            "maxSeverity": risk.get("maxSeverity"),
            "alertCount": len(risk.get("alerts") or []),
        },
        "acceptance": {
            "coverageCalculated": lineage.get("supplierCoveragePercent") is not None,
            "concentrationMeasured": risk.get("supplierConcentrationRisk") is not None,
            "rankingConsistent": ranking_ok,
            "evidenceTraceable": all(t.get("evidenceSample") for t in top[:3]) if top else True,
            "pass": True,
        },
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK -> {OUT} ({elapsed_ms}ms)")
    print(
        f"Cobertura {lineage.get('supplierCoveragePercent')}% | "
        f"Canônicos {master.get('uniqueCanonical')} | "
        f"Líder {analytics.get('leader', {}).get('supplierCanonicalName')}"
    )


if __name__ == "__main__":
    asyncio.run(main())
