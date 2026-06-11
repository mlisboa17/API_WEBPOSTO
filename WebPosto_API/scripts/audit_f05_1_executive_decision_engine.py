#!/usr/bin/env python3
"""F05.1 — Executive Decision Engine audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.executive_decision_engine_service import ExecutiveDecisionEngineService
from src.services.executive_decision_engine_snapshot_service import ExecutiveDecisionEngineSnapshotService

WINDOWS = {"7d": ("2026-06-01", "2026-06-07")}


async def audit_window(svc, snap, label, di, df) -> dict:
    t0 = time.perf_counter()
    resp = await svc.build(di, df, None)
    build_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not resp.success or not resp.data:
        return {"window": label, "error": str(resp.error), "buildMs": build_ms}
    data = resp.data
    await snap.collect(di, df, None, data)
    ex = data.get("executiveAnswers") or {}
    qa = data.get("qa") or {}
    return {
        "window": label,
        "buildMs": build_ms,
        "executiveAnswers": ex,
        "qa": qa,
        "parecerFinal": data.get("parecerFinal"),
        "decisaoArquitetural": data.get("decisaoArquitetural"),
        "cockpit": data.get("cockpit"),
        "planoCorporativoConsolidado": data.get("planoCorporativoConsolidado"),
        "roiPrioritizationEngine": {
            "total": (data.get("roiPrioritizationEngine") or {}).get("total"),
            "prioridade1": len((data.get("roiPrioritizationEngine") or {}).get("prioridade1") or []),
        },
    }


async def main() -> None:
    svc = ExecutiveDecisionEngineService()
    snap = ExecutiveDecisionEngineSnapshotService(svc)
    results = {"sprint": "F05.1", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        print(f"F05.1 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        ex = w.get("executiveAnswers") or {}
        print(
            f"  done trust={ex.get('trustExecutivo')} "
            f"p1={len((w.get('planoCorporativoConsolidado') or {}).get('prioridade1') or [])} "
            f"parecer={w.get('parecerFinal')}",
            flush=True,
        )

    ref = results["windows"]["7d"]
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qa") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "fonteWebPosto": False,
        "trustExecutivoOk": bool(qa.get("trustExecutivoOk")),
        "planoCorporativo": bool(ex.get("14_planoCorporativoConsolidado")),
        "cockpit": bool(ref.get("cockpit")),
        "paridadeZero": bool(qa.get("paridadeZero")),
        "auditavel": bool(qa.get("auditavel")),
        "aprovadoF052": bool(ex.get("20_aprovadoF052")),
    }

    out = ROOT / "scripts" / "f05_1_executive_decision_engine.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
