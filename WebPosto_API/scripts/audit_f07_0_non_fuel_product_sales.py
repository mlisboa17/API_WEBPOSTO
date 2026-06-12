#!/usr/bin/env python3
"""F07.0 — Non-Fuel Product Sales audit."""
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
        "executiveAnswers": data.get("executiveAnswers") or {},
        "qa": data.get("qa") or {},
        "parecerFinal": data.get("parecerFinal"),
        "cockpit": data.get("cockpit"),
        "multiTenantScalabilityEngine": data.get("multiTenantScalabilityEngine"),
        "productDepartmentDiscovery": data.get("productDepartmentDiscovery"),
        "nonFuelSalesEngine": data.get("nonFuelSalesEngine"),
        "productRankingEngine": data.get("productRankingEngine"),
        "branchDepartmentAnalytics": data.get("branchDepartmentAnalytics"),
        "productSalesLineage": data.get("productSalesLineage"),
        "dwLayer": data.get("dwLayer"),
    }


async def main() -> None:
    svc = NonFuelProductSalesService()
    snap = NonFuelProductSalesSnapshotService(svc)
    results = {"sprint": "F07.0", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
    out = ROOT / "scripts" / "f07_0_non_fuel_product_sales.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    w = results["windows"].get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    print(f"F07.0 audit OK — buildMs={w.get('buildMs')}")
    print(f"  valor NF: R$ {ex.get('4_valorTotalNaoCombustivel')}")
    print(f"  itens NF: {ex.get('5_quantidadeItensNaoCombustivel')}")
    print(f"  participacao NF: {ex.get('7_participacaoNaoCombustivel')}%")
    print(f"  parecer: {w.get('parecerFinal')}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
