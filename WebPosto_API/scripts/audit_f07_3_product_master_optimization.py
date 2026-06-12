#!/usr/bin/env python3
"""F07.3 — Product Master Optimization audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.non_fuel_product_sales_snapshot_service import NonFuelProductSalesSnapshotService
from src.services.product_master_optimization_service import ProductMasterOptimizationService

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
        "residualSkuForensics": data.get("residualSkuForensics"),
        "productLookupOptimization": data.get("productLookupOptimization"),
        "productCacheStrategy": data.get("productCacheStrategy"),
        "departmentRefinement": data.get("departmentRefinement"),
        "multiBranchProductScale": data.get("multiBranchProductScale"),
        "productPerformanceBenchmark": data.get("productPerformanceBenchmark"),
        "productMasterCoverage": data.get("productMasterCoverage"),
        "productMatchRecovery": data.get("productMatchRecovery"),
        "cockpit": data.get("cockpit"),
        "dwLayer": data.get("dwLayer"),
    }


async def main() -> None:
    svc = ProductMasterOptimizationService()
    snap = NonFuelProductSalesSnapshotService(svc)
    results = {"sprint": "F07.3", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
    out = ROOT / "scripts" / "f07_3_product_master_optimization.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    w = results["windows"].get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    bench = w.get("productPerformanceBenchmark") or {}
    forensics = w.get("residualSkuForensics") or {}
    print(f"F07.3 audit OK — buildMs={w.get('buildMs')} fonte={w.get('fonte', {}).get('modo')}")
    print(f"  SKU 1975728: {forensics.get('classificacaoFinal')} — {forensics.get('nomeResolvido')}")
    print(f"  sem cadastro: {ex.get('3_produtosSemCadastroRestantes')}")
    print(f"  cobertura: {ex.get('4_coberturaCatalogoFinal')}%")
    print(f"  lookup: {bench.get('tempoTotalLookupDepoisSec')}s (antes {bench.get('tempoTotalLookupAntesSec')}s)")
    print(f"  redução: {bench.get('reducaoPercentual')}% | cache hit: {bench.get('cacheHitRatePct')}%")
    print(f"  parecer: {w.get('parecerFinal')}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
