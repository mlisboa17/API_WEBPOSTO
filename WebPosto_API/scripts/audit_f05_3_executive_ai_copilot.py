#!/usr/bin/env python3
"""F05.3 — Executive AI Copilot audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.executive_ai_copilot_service import ExecutiveAiCopilotService
from src.services.executive_ai_copilot_snapshot_service import ExecutiveAiCopilotSnapshotService

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
        "governanceLayer": data.get("governanceLayer"),
        "hallucinationChallenge": data.get("hallucinationChallenge"),
        "recommendationEngine": {
            "total": (data.get("recommendationEngine") or {}).get("total"),
            "byLevel": (data.get("recommendationEngine") or {}).get("byLevel"),
        },
    }


async def main() -> None:
    svc = ExecutiveAiCopilotService()
    snap = ExecutiveAiCopilotSnapshotService(svc)
    results = {"sprint": "F05.3", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        print(f"F05.3 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        ex = w.get("executiveAnswers") or {}
        print(
            f"  done perguntas={ex.get('5_perguntasHomologadas')} recs={ex.get('6_totalRecomendacoes')} "
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
        "semRespostaSemEvidencia": bool(qa.get("semRespostaSemEvidencia")),
        "semRespostaSemConfidence": bool(qa.get("semRespostaSemConfidence")),
        "semCrossTenant": bool(qa.get("semCrossTenant")),
        "semRoiSemOrigem": bool(qa.get("semRoiSemOrigem")),
        "semAlucinacao": bool(qa.get("semAlucinacao")),
        "auditavel": bool(qa.get("auditavel")),
        "aprovadoF054": bool(ex.get("20_aprovadoF054")),
    }

    out = ROOT / "scripts" / "f05_3_executive_ai_copilot.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
