#!/usr/bin/env python3
"""F07.1 — Produtos Vendidos catálogo & departamentalização audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.non_fuel_product_sales_service import NonFuelProductSalesService
from src.services.non_fuel_product_sales_snapshot_service import NonFuelProductSalesSnapshotService

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
        "paginationEngine": data.get("paginationEngine"),
        "productCatalogCompleteness": data.get("productCatalogCompleteness"),
        "productDepartmentClassification": data.get("productDepartmentClassification"),
        "salesCoverageReconciliation": data.get("salesCoverageReconciliation"),
        "produtosVendidosKpiEngine": data.get("produtosVendidosKpiEngine"),
        "productRankingEngine": data.get("productRankingEngine"),
        "branchProductAnalytics": data.get("branchProductAnalytics"),
        "productSalesLineage": data.get("productSalesLineage"),
        "cockpit": data.get("cockpit"),
        "dwLayer": data.get("dwLayer"),
    }


async def main() -> None:
    svc = NonFuelProductSalesService()
    snap = NonFuelProductSalesSnapshotService(svc)
    results = {"sprint": "F07.1", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
    out = ROOT / "scripts" / "f07_1_produtos_vendidos_catalogo_departamentalizacao.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    w = results["windows"].get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    rec = w.get("salesCoverageReconciliation") or {}
    print(f"F07.1 audit OK — buildMs={w.get('buildMs')} fonte={w.get('fonte', {}).get('modo')}")
    print(f"  produtos catálogo: {ex.get('1_produtosNoCatalogoCompleto')}")
    print(f"  produtos vendidos: {ex.get('2_produtosVendidos')}")
    print(f"  receita PV: R$ {ex.get('5_receitaTotalProdutosVendidos')}")
    print(f"  gap F07.0: R$ {ex.get('14_gapF070vsF071')}")
    print(f"  parecer: {w.get('parecerFinal')}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
