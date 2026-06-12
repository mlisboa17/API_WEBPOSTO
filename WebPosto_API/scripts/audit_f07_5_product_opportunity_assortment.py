#!/usr/bin/env python3
"""F07.5 — Product Opportunity & Assortment Intelligence audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.non_fuel_product_sales_snapshot_service import NonFuelProductSalesSnapshotService
from src.services.product_opportunity_assortment_service import ProductOpportunityAssortmentService

WINDOWS = {"7d": ("2026-06-01", "2026-06-07")}


async def audit_window(svc, snap, label, di, df) -> dict:
    t0 = time.perf_counter()
    resp = await svc.build(di, df, None)
    build_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not resp.success or not resp.data:
        return {"window": label, "error": str(resp.error), "buildMs": build_ms}
    data = resp.data
    await snap.collect(di, df, None, data)
    assortment = data.get("productOpportunityAssortment") or {}
    return {
        "window": label,
        "buildMs": build_ms,
        "fonte": data.get("fonte"),
        "executiveAnswers": data.get("executiveAnswers"),
        "qa": data.get("qa"),
        "parecerFinal": data.get("parecerFinal"),
        "productOpportunityAssortment": assortment,
        "marginIntelligence": data.get("marginIntelligence"),
        "mixHealthCommercial": data.get("mixHealthCommercial"),
        "cockpit": data.get("cockpit"),
        "dwLayer": data.get("dwLayer"),
    }


async def main() -> None:
    svc = ProductOpportunityAssortmentService()
    snap = NonFuelProductSalesSnapshotService(svc)
    results = {"sprint": "F07.5", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
    out = ROOT / "scripts" / "f07_5_product_opportunity_assortment.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    w = results["windows"].get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    ass = w.get("productOpportunityAssortment") or {}
    print(f"F07.5 audit OK — buildMs={w.get('buildMs')} fonte={w.get('fonte', {}).get('modo')}")
    print(f"  top margem: {ex.get('1_produtoMaiorMargemPct')} ({ex.get('2_margemPctLider')}%)")
    print(f"  alertas baixa margem: {ex.get('3_produtosAltoVolumeBaixaMargem')}")
    print(f"  potencial expansão: {ex.get('5_produtosPotencialExpansao')}")
    print(f"  filiais abaixo benchmark: {ex.get('7_filiaisAbaixoBenchmarkMix')}")
    print(f"  foco comercial: {ex.get('9_produtosFocoComercial')}")
    print(f"  dep. combustível: {ex.get('11_filiaisDependenciaCombustivel')}")
    print(f"  parecer: {w.get('parecerFinal')}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
