#!/usr/bin/env python3
"""F05.0 — Corporate Intelligence Hub audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.corporate_intelligence_hub_service import CorporateIntelligenceHubService
from src.services.corporate_intelligence_hub_snapshot_service import CorporateIntelligenceHubSnapshotService

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
        "paridadeDelta": ex.get("paridadeDelta"),
        "cockpit": data.get("cockpit"),
        "corporateKpiConsolidation": data.get("corporateKpiConsolidation"),
        "opportunityEngine": data.get("opportunityEngine"),
        "riskIntelligenceEngine": data.get("riskIntelligenceEngine"),
    }


async def main() -> None:
    svc = CorporateIntelligenceHubService()
    snap = CorporateIntelligenceHubSnapshotService(svc)
    results = {"sprint": "F05.0", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        print(f"F05.0 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        print(
            f"  done corporate={w.get('executiveAnswers', {}).get('1_corporateScore')} "
            f"paridade={w.get('paridadeDelta')} parecer={w.get('parecerFinal')}",
            flush=True,
        )

    ref = results["windows"]["7d"]
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qa") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "fonteWebPosto": False,
        "corporateScore": bool(ex.get("1_corporateScore")),
        "cockpit": bool(ref.get("cockpit")),
        "paridadeZero": bool(qa.get("paridadeZero")),
        "opportunityEngine": bool(ref.get("opportunityEngine")),
        "riskEngine": bool(ref.get("riskIntelligenceEngine")),
        "aprovado": bool(ex.get("20_aprovadoF051")),
    }

    out = ROOT / "scripts" / "f05_0_corporate_intelligence_hub.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
