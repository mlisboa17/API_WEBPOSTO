#!/usr/bin/env python3
"""F04.3 — Store & Shift Profitability audit."""
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

from src.services.store_shift_profitability_service import StoreShiftProfitabilityService
from src.services.store_shift_profitability_snapshot_service import StoreShiftProfitabilitySnapshotService

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
        "periodo": {"inicio": di, "fim": df},
        "buildMs": build_ms,
        "executiveAnswers": ex,
        "qa": qa,
        "parecerFinal": data.get("parecerFinal"),
        "paridadeDelta": ex.get("paridadeDelta"),
        "paridadeReceitaPdv": ex.get("paridadeReceitaPdv"),
        "paridadeReceitaConsolidada": ex.get("paridadeReceitaConsolidada"),
        "operationBands": (data.get("operationMatrixEngine") or {}).get("bands"),
        "cockpit": data.get("cockpit"),
        "criticalPdvForensics": data.get("criticalPdvForensics"),
    }


async def main() -> None:
    svc = StoreShiftProfitabilityService()
    snap = StoreShiftProfitabilitySnapshotService(svc)
    results = {"sprint": "F04.3", "windows": {}}

    for label, (di, df) in WINDOWS.items():
        print(f"F04.3 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        print(f"  done paridade={w.get('paridadeDelta')} parecer={w.get('parecerFinal')}", flush=True)

    ref = results["windows"]["7d"]
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qa") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "roiPdv": bool(qa.get("roiPdvOk")),
        "roiTurno": bool(qa.get("roiTurnoOk")),
        "attribution": bool(qa.get("attributionOk")),
        "cockpit": bool(qa.get("cockpitOk")),
        "paridadeZero": bool(qa.get("paridadeZero")),
        "aprovado": bool(ex.get("20_aprovadoF044")),
    }

    out = ROOT / "scripts" / "f04_3_store_shift_profitability.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
