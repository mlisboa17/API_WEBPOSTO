#!/usr/bin/env python3
"""F07.7 — Commercial Execution & Outcome Tracking audit (100% snapshots homologados)."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.commercial_execution_service import CommercialExecutionService
from src.services.commercial_execution_snapshot_service import CommercialExecutionSnapshotService

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
        "commercialAssignmentEngine": data.get("commercialAssignmentEngine"),
        "commercialExecutionTracking": data.get("commercialExecutionTracking"),
        "commercialEvidenceEngine": data.get("commercialEvidenceEngine"),
        "commercialOutcomeMeasurement": data.get("commercialOutcomeMeasurement"),
        "revenueLiftTracking": data.get("revenueLiftTracking"),
        "marginImprovementTracking": data.get("marginImprovementTracking"),
        "commercialPerformance": data.get("commercialPerformance"),
        "cockpit": data.get("cockpit"),
        "dwLayer": data.get("dwLayer"),
    }


async def main() -> None:
    svc = CommercialExecutionService()
    snap = CommercialExecutionSnapshotService(svc)
    results = {"sprint": "F07.7", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
    out = ROOT / "scripts" / "f07_7_commercial_execution.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    w = results["windows"].get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    rev = w.get("revenueLiftTracking") or {}
    qa = w.get("qa") or {}
    print(f"F07.7 audit OK — buildMs={w.get('buildMs')} fonte={w.get('fonte', {}).get('modo')}")
    print(f"  ações: {ex.get('1_totalAcoes')}")
    print(f"  executadas: {ex.get('2_acoesExecutadas')}")
    print(f"  validadas: {ex.get('3_acoesValidadas')}")
    print(f"  receita realizada: R$ {rev.get('receitaRealizada')}")
    print(f"  QA auditável: {qa.get('motorAuditavel')}")
    print(f"  parecer: {w.get('parecerFinal')}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
