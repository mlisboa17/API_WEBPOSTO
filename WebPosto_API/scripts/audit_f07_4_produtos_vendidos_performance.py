#!/usr/bin/env python3
"""F07.4 — Produtos Vendidos Performance & Margin Intelligence audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.non_fuel_product_sales_snapshot_service import NonFuelProductSalesSnapshotService
from src.services.produtos_vendidos_performance_service import ProdutosVendidosPerformanceService

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
        "productSalesPerformance": data.get("productSalesPerformance"),
        "marginIntelligence": data.get("marginIntelligence"),
        "mixHealthCommercial": data.get("mixHealthCommercial"),
        "opportunityEngine": data.get("opportunityEngine"),
        "productMasterCoverage": data.get("productMasterCoverage"),
        "cockpit": data.get("cockpit"),
        "dwLayer": data.get("dwLayer"),
    }


async def main() -> None:
    svc = ProdutosVendidosPerformanceService()
    snap = NonFuelProductSalesSnapshotService(svc)
    results = {"sprint": "F07.4", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
    out = ROOT / "scripts" / "f07_4_produtos_vendidos_performance.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    w = results["windows"].get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    perf = w.get("productSalesPerformance") or {}
    margin = w.get("marginIntelligence") or {}
    mix = w.get("mixHealthCommercial") or {}
    opp = w.get("opportunityEngine") or {}
    print(f"F07.4 audit OK — buildMs={w.get('buildMs')} fonte={w.get('fonte', {}).get('modo')}")
    print(f"  top volume: {ex.get('1_produtoMaisVendidoVolume')}")
    print(f"  top receita: {ex.get('2_produtoMaiorReceita')}")
    print(f"  filial top: {ex.get('3_filialMelhorPerformance')}")
    print(f"  receita PV: R$ {ex.get('4_receitaProdutosVendidos')}")
    print(f"  margem: R$ {ex.get('5_margemBrutaTotal')} ({ex.get('6_margemBrutaPct')}%)")
    print(f"  mix saudável: {ex.get('7_mixSaudavel')}")
    print(f"  oportunidades: {opp.get('totalOportunidades')}")
    print(f"  parecer: {w.get('parecerFinal')}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
