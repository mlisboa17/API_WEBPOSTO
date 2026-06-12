#!/usr/bin/env python3
"""F06.4 — Fiscal Reconciliation Hub audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.fiscal_reconciliation_hub_service import FiscalReconciliationHubService
from src.services.fiscal_reconciliation_hub_snapshot_service import FiscalReconciliationHubSnapshotService

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
        "fiscalLineageEngine": data.get("fiscalLineageEngine"),
        "nfceVendaReconciliation": data.get("nfceVendaReconciliation"),
        "productSalesReconciliation": data.get("productSalesReconciliation"),
        "lmcSalesReconciliation": data.get("lmcSalesReconciliation"),
        "fiscalFinancialBridge": data.get("fiscalFinancialBridge"),
        "fiscalRiskConsolidation": data.get("fiscalRiskConsolidation"),
        "dwLayer": data.get("dwLayer"),
    }


async def main() -> None:
    svc = FiscalReconciliationHubService()
    snap = FiscalReconciliationHubSnapshotService(svc)
    results = {"sprint": "F06.4", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
    out = ROOT / "scripts" / "f06_4_fiscal_reconciliation_hub.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    w = results["windows"].get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    qa = w.get("qa") or {}
    print(f"F06.4 audit OK — buildMs={w.get('buildMs')}")
    print(f"  vendas×NFCE: {ex.get('1_vendasConciliadasNfce')}")
    print(f"  sem NFCE: {ex.get('2_vendasSemNfce')}")
    print(f"  litros sem LMC: {ex.get('6_litrosSemLmc')}")
    print(f"  maior risco: {ex.get('9_maiorRiscoConsolidado')}")
    print(f"  motor auditável: {qa.get('motorAuditavel')}")
    print(f"  parecer: {w.get('parecerFinal')}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
