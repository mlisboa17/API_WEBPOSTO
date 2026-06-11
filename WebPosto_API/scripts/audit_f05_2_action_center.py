#!/usr/bin/env python3
"""F05.2 — Action Center audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.action_center_service import ActionCenterService
from src.services.action_center_snapshot_service import ActionCenterSnapshotService

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
        "cockpit": data.get("cockpit"),
        "executionTrackingEngine": data.get("executionTrackingEngine"),
        "roiRealizationEngine": data.get("roiRealizationEngine"),
        "governanceRules": data.get("governanceRules"),
    }


async def main() -> None:
    svc = ActionCenterService()
    snap = ActionCenterSnapshotService(svc)
    results = {"sprint": "F05.2", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        print(f"F05.2 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        ex = w.get("executiveAnswers") or {}
        print(
            f"  done acoes={ex.get('1_totalAcoes')} nominal={ex.get('2_donoNominal')} "
            f"validadas={ex.get('6_validadas')} parecer={w.get('parecerFinal')}",
            flush=True,
        )

    ref = results["windows"]["7d"]
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qa") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "fonteWebPosto": False,
        "semDonoNominal": bool(qa.get("semDonoNominal")),
        "semValidadaSemEvidencia": bool(qa.get("semValidadaSemEvidencia")),
        "semRoiFragilRealizado": bool(qa.get("semRoiRealizadoFragil")),
        "auditavel": bool(qa.get("auditavel")),
        "aprovadoF053": bool(ex.get("20_aprovadoF053")),
    }

    out = ROOT / "scripts" / "f05_2_action_center.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
