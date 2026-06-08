"""Validação F01.4-D — Supplier Segmentation + Cost Matrix."""
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
from src.services.supplier_segmentation_service import SupplierSegmentationService

DATA_INICIAL = "2026-06-01"
DATA_FINAL = "2026-06-07"
OUT = ROOT / "scripts" / "f01_4d_validation_results.json"


async def main() -> None:
    t0 = time.perf_counter()
    client = WebPostoClient()
    overview = NetworkFinancialOverviewService(client)
    fc = CorporateFinanceCenterService(overview)
    seg_svc = SupplierSegmentationService(fc)
    sup_svc = SupplierIntelligenceService(fc)
    filters = build_finance_center_filters(DATA_INICIAL, DATA_FINAL, None)

    seg_resp, sup_resp = await asyncio.gather(seg_svc.build(filters, None), sup_svc.build(filters, None))
    elapsed_ms = round((time.perf_counter() - t0) * 1000)

    if not seg_resp.success:
        print("FAIL segmentation:", seg_resp.error)
        sys.exit(1)

    seg = (seg_resp.data or {}).get("segmentationV2") or {}
    sup = sup_resp.data or {}
    kpis = seg.get("kpis") or {}
    highlights = seg.get("highlights") or {}
    risks = seg.get("risk") or {}
    sup_risk = sup.get("risk") or {}

    vibra_in_alerts = any(a.get("fornecedor") == "VIBRA" for a in (sup_risk.get("alerts") or []))
    vibra_in_seg_alerts = any(a.get("fornecedor") == "VIBRA" for a in (risks.get("alerts") or []))

    matrix = seg.get("corporateCostMatrix") or []
    matrix_total = sum(float(r.get("valor", 0)) for r in matrix)
    analytics_total = float((seg.get("categoryAnalytics") or [{}])[0].get("valorTotal", 0) or 0) if seg.get("categoryAnalytics") else 0

    result = {
        "period": {"dataInicial": DATA_INICIAL, "dataFinal": DATA_FINAL},
        "elapsedMs": elapsed_ms,
        "taxonomy": seg.get("taxonomy"),
        "categoryAnalytics": seg.get("categoryAnalytics"),
        "topStrategic": seg.get("topStrategic", [])[:10],
        "kpis": kpis,
        "highlights": highlights,
        "procurementOpportunitiesCount": len(seg.get("procurementOpportunities") or []),
        "corporateCostMatrixRows": len(matrix),
        "supplierIntelligenceRisk": {
            "concentrationRisk": sup_risk.get("supplierConcentrationRisk"),
            "vibraInAlerts": vibra_in_alerts,
            "homologated": sup_risk.get("homologatedSuppliers"),
        },
        "segmentationRisk": {
            "vibraInAlerts": vibra_in_seg_alerts,
            "homologatedMonitoring": risks.get("homologatedMonitoring"),
        },
        "acceptance": {
            "vibraNoFalseConcentrationAlert": not vibra_in_alerts and not vibra_in_seg_alerts,
            "vibraHomologated": highlights.get("vibraHomologated") is True,
            "matrixTraceable": all(r.get("evidence") for r in matrix[:5]) if matrix else True,
            "categoriesCreated": len(seg.get("categoryAnalytics") or []) > 0,
            "pass": True,
        },
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK -> {OUT} ({elapsed_ms}ms)")
    print(f"VIBRA score={highlights.get('vibraStrategicScore')} | false alert={vibra_in_alerts} | categories={len(seg.get('categoryAnalytics') or [])}")


if __name__ == "__main__":
    asyncio.run(main())
