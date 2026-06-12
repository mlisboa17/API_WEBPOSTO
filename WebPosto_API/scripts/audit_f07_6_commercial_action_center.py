#!/usr/bin/env python3
"""F07.6 — Commercial Action Center audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.commercial_action_center_service import CommercialActionCenterService
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
    cac = data.get("commercialActionCenter") or {}
    return {
        "window": label,
        "buildMs": build_ms,
        "fonte": data.get("fonte"),
        "executiveAnswers": data.get("executiveAnswers"),
        "qa": data.get("qa"),
        "parecerFinal": data.get("parecerFinal"),
        "commercialActionCenter": cac,
        "cockpit": data.get("cockpit"),
        "dwLayer": data.get("dwLayer"),
    }


async def main() -> None:
    svc = CommercialActionCenterService()
    snap = NonFuelProductSalesSnapshotService(svc)
    results = {"sprint": "F07.6", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
    out = ROOT / "scripts" / "f07_6_commercial_action_center.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    w = results["windows"].get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    cac = w.get("commercialActionCenter") or {}
    summary = cac.get("summary") or {}
    print(f"F07.6 audit OK — buildMs={w.get('buildMs')} fonte={w.get('fonte', {}).get('modo')}")
    print(f"  ações: {summary.get('totalAcoes')}")
    print(f"  alta prioridade: {summary.get('acoesAltaPrioridade')}")
    print(f"  impacto receita: R$ {summary.get('impactoTotalReceita')}")
    print(f"  parecer: {w.get('parecerFinal')}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
