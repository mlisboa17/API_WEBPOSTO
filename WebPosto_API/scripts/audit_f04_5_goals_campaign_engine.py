#!/usr/bin/env python3
"""F04.5 — Goals & Campaign Engine audit."""
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

from src.services.goals_campaign_engine_service import GoalsCampaignEngineService
from src.services.goals_campaign_engine_snapshot_service import GoalsCampaignEngineSnapshotService

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
        "paridadeDelta": ex.get("paridadeDelta"),
        "cockpit": data.get("cockpit"),
    }


async def main() -> None:
    svc = GoalsCampaignEngineService()
    snap = GoalsCampaignEngineSnapshotService(svc)
    results = {"sprint": "F04.5", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        print(f"F04.5 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        print(f"  done paridade={w.get('paridadeDelta')} parecer={w.get('parecerFinal')}", flush=True)

    ref = results["windows"]["7d"]
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qa") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "goalEngine": bool(ex.get("1_metasCriadas")),
        "campaignEngine": bool(ex.get("2_campanhasSimuladas")),
        "cockpit": bool(ref.get("cockpit")),
        "paridadeZero": bool(qa.get("paridadeZero")),
        "evidenciaCompleta": bool(qa.get("evidenciaCompleta")),
        "aprovado": bool(ex.get("15_prontoF046")),
    }

    out = ROOT / "scripts" / "f04_5_goals_campaign_engine.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
