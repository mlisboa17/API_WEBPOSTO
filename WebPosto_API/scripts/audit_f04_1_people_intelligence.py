#!/usr/bin/env python3
"""F04.1 — Operator Accountability & Incentive Engine audit."""
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

from src.services.operator_accountability_incentive_service import OperatorAccountabilityIncentiveService
from src.services.operator_accountability_incentive_snapshot_service import (
    OperatorAccountabilityIncentiveSnapshotService,
)

WINDOWS = {
    "7d": ("2026-06-01", "2026-06-07"),
    "30d": ("2026-05-08", "2026-06-07"),
    "90d": ("2026-03-09", "2026-06-07"),
}


async def audit_window(
    svc: OperatorAccountabilityIncentiveService,
    snap: OperatorAccountabilityIncentiveSnapshotService,
    label: str,
    di: str,
    df: str,
) -> dict:
    t0 = time.perf_counter()
    resp = await svc.build(di, df, None)
    build_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not resp.success or not resp.data:
        return {"window": label, "error": str(resp.error), "buildMs": build_ms}

    data = resp.data
    await snap.collect(di, df, None, data)
    master = snap.get_master(di, df, None)
    snap_payload = master.get("payload") or {}

    live_par = (data.get("executiveAnswers") or {}).get("paridadeDelta", 999)
    snap_par = (snap_payload.get("executiveAnswers") or {}).get("paridadeDelta", 999)
    parity_ok = abs(float(live_par or 0) - float(snap_par or 0)) <= 0.01 and float(live_par or 999) <= 0.01

    cls = (data.get("operatorClassification") or {}).get("summary") or {}
    qa = data.get("qa") or {}

    return {
        "window": label,
        "periodo": {"inicio": di, "fim": df},
        "buildMs": build_ms,
        "classification": cls,
        "executiveAnswers": data.get("executiveAnswers"),
        "qa": qa,
        "parecerFinal": data.get("parecerFinal"),
        "paridadeDelta": live_par,
        "paridadeOk": parity_ok,
        "cockpit": data.get("cockpit"),
        "scores": {
            "sales": len((data.get("salesScoreEngine") or {}).get("operators") or []),
            "productivity": len((data.get("productivityScoreEngine") or {}).get("operators") or []),
            "accountability": len((data.get("cashAccountabilityScore") or {}).get("operators") or []),
            "compliance": len((data.get("complianceScoreEngine") or {}).get("operators") or []),
        },
    }


async def main() -> None:
    only = __import__("os").environ.get("F04_WINDOW")
    windows = {only: WINDOWS[only]} if only and only in WINDOWS else {"7d": WINDOWS["7d"]}

    svc = OperatorAccountabilityIncentiveService()
    snap = OperatorAccountabilityIncentiveSnapshotService(svc)
    results: dict = {"sprint": "F04.1", "windows": {}}

    for label, (di, df) in windows.items():
        print(f"F04.1 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        print(
            f"  done paridade={w.get('paridadeDelta')} parecer={w.get('parecerFinal')}",
            flush=True,
        )

    ref = results["windows"].get("7d") or next(iter(results["windows"].values()), {})
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qa") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "fourScores": bool(qa.get("fourScoresOk")),
        "globalScore": bool(qa.get("globalScoreOk")),
        "bonusEligibility": bool(qa.get("bonusEligibilityOk")),
        "training": bool(qa.get("trainingOk")),
        "classification": bool(qa.get("classificationOk")),
        "paridadeZero": bool(qa.get("paridadeZero")),
        "aprovado": bool(ex.get("20_aprovadoF042")),
    }

    out = ROOT / "scripts" / "f04_1_people_intelligence.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
