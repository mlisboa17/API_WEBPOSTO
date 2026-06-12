#!/usr/bin/env python3
"""F07.2 — Product Master Enrichment audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.non_fuel_product_sales_snapshot_service import NonFuelProductSalesSnapshotService
from src.services.product_master_enrichment_service import ProductMasterEnrichmentService

WINDOWS = {"7d": ("2026-06-01", "2026-06-07")}


async def audit_window(svc, snap, label, di, df) -> dict:
    t0 = time.perf_counter()
    resp = await svc.build(di, df, None)
    build_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not resp.success or not resp.data:
        return {"window": label, "error": str(resp.error), "buildMs": build_ms}
    data = resp.data
    await snap.collect(di, df, None, data)
    return {
        "window": label,
        "buildMs": build_ms,
        "fonte": data.get("fonte"),
        "executiveAnswers": data.get("executiveAnswers"),
        "qa": data.get("qa"),
        "parecerFinal": data.get("parecerFinal"),
        "productMasterCoverage": data.get("productMasterCoverage"),
        "productMatchRecovery": data.get("productMatchRecovery"),
        "productHierarchyDiscovery": data.get("productHierarchyDiscovery"),
        "departmentIntelligence": data.get("departmentIntelligence"),
        "productRevenueIntelligence": data.get("productRevenueIntelligence"),
        "branchProductMix": data.get("branchProductMix"),
        "produtosVendidosKpiEngine": data.get("produtosVendidosKpiEngine"),
        "productRankingEngine": data.get("productRankingEngine"),
        "cockpit": data.get("cockpit"),
        "dwLayer": data.get("dwLayer"),
    }


async def main() -> None:
    svc = ProductMasterEnrichmentService()
    snap = NonFuelProductSalesSnapshotService(svc)
    results = {"sprint": "F07.2", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
    out = ROOT / "scripts" / "f07_2_product_master_enrichment.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    w = results["windows"].get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    rec = w.get("productMatchRecovery") or {}
    cov = w.get("productMasterCoverage") or {}
    print(f"F07.2 audit OK — buildMs={w.get('buildMs')} fonte={w.get('fonte', {}).get('modo')}")
    print(f"  cobertura F07.1: {cov.get('coberturaCatalogoAtualPct')}%")
    print(f"  cobertura final: {cov.get('coberturaCatalogoFinalPct')}%")
    print(f"  recuperados: {rec.get('produtosRecuperados')} / antes {rec.get('antesSemMatch')}")
    print(f"  sem match final: {rec.get('depoisSemMatch')}")
    print(f"  receita PV: R$ {ex.get('10_receitaProdutosVendidos')}")
    print(f"  parecer: {w.get('parecerFinal')}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
