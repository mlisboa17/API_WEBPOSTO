#!/usr/bin/env python3
"""F04.4 — Management Action Center audit."""
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

from src.services.management_action_center_service import ManagementActionCenterService
from src.services.management_action_center_snapshot_service import ManagementActionCenterSnapshotService

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
        "governanceBands": (data.get("peopleGovernanceEngine") or {}).get("bands"),
        "actionCounts": (data.get("actionEngine") or {}).get("actionCounts"),
        "cockpit": data.get("cockpit"),
    }


async def main() -> None:
    svc = ManagementActionCenterService()
    snap = ManagementActionCenterSnapshotService(svc)
    results = {"sprint": "F04.4", "windows": {}}

    for label, (di, df) in WINDOWS.items():
        print(f"F04.4 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        print(f"  done paridade={w.get('paridadeDelta')} parecer={w.get('parecerFinal')}", flush=True)

    ref = results["windows"]["7d"]
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qa") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "actionEngine": bool((ref.get("actionCounts") or {})),
        "governance": bool(ref.get("governanceBands")),
        "promotions": bool(ex.get("1_elegiveisPromocao") is not None),
        "bonus": bool(ex.get("2_elegiveisBonus") is not None),
        "training": bool(ex.get("3_precisamTreinamento") is not None),
        "cockpit": bool(ref.get("cockpit")),
        "paridadeZero": bool(qa.get("paridadeZero")),
        "evidenciaCompleta": bool(qa.get("evidenciaCompleta")),
        "aprovado": bool(ex.get("20_aprovadoF045")),
    }

    out = ROOT / "scripts" / "f04_4_management_action_center.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
