#!/usr/bin/env python3
"""F04.2 — Operator Profitability & ROI audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from src.services.operator_profitability_service import OperatorProfitabilityService
from src.services.operator_profitability_snapshot_service import OperatorProfitabilitySnapshotService

WINDOWS = {"7d": ("2026-06-01", "2026-06-07")}


async def audit_window(svc, snap, label, di, df) -> dict:
    t0 = time.perf_counter()
    resp = await svc.build(di, df, None)
    build_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not resp.success or not resp.data:
        return {"window": label, "error": str(resp.error), "buildMs": build_ms}

    data = resp.data
    await snap.collect(di, df, None, data)
    master = snap.get_master(di, df, None)
    snap_payload = master.get("payload") or {}

    ex = data.get("executiveAnswers") or {}
    live_par = ex.get("paridadeDelta", 999)
    snap_par = (snap_payload.get("executiveAnswers") or {}).get("paridadeDelta", 999)
    parity_ok = abs(float(live_par or 0) - float(snap_par or 0)) <= 0.01 and float(live_par or 999) <= 0.01

    return {
        "window": label,
        "periodo": {"inicio": di, "fim": df},
        "buildMs": build_ms,
        "executiveAnswers": ex,
        "qa": data.get("qa"),
        "parecerFinal": data.get("parecerFinal"),
        "paridadeDelta": live_par,
        "paridadeOk": parity_ok,
        "paridadeReceitaOperador": ex.get("paridadeReceitaOperador"),
        "paridadeReceitaConsolidada": ex.get("paridadeReceitaConsolidada"),
        "profitabilityBands": (data.get("profitabilityScoreEngine") or {}).get("bands"),
        "cockpit": data.get("cockpit"),
    }


async def main() -> None:
    svc = OperatorProfitabilityService()
    snap = OperatorProfitabilitySnapshotService(svc)
    results = {"sprint": "F04.2", "windows": {}}

    for label, (di, df) in WINDOWS.items():
        print(f"F04.2 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        print(f"  done paridade={w.get('paridadeDelta')} parecer={w.get('parecerFinal')}", flush=True)

    ref = results["windows"]["7d"]
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qa") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "profitabilityScore": bool(qa.get("profitabilityScoreOk")),
        "roi": bool(qa.get("roiOk")),
        "managementActions": bool(qa.get("managementActionsOk")),
        "cockpit": bool(qa.get("cockpitOk")),
        "paridadeZero": bool(qa.get("paridadeZero")),
        "aprovado": bool(ex.get("20_aprovadoF043")),
    }

    out = ROOT / "scripts" / "f04_2_operator_profitability.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
