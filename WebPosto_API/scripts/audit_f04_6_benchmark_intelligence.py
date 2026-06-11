#!/usr/bin/env python3
"""F04.6 — Benchmark Intelligence (somente snapshots)."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.benchmark_intelligence_service import BenchmarkIntelligenceService
from src.services.benchmark_intelligence_snapshot_service import BenchmarkIntelligenceSnapshotService

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
        "companyBenchmark": data.get("companyBenchmark"),
        "operatorBenchmark": data.get("operatorBenchmark"),
        "gapEngine": data.get("gapEngine"),
        "bestPracticesEngine": data.get("bestPracticesEngine"),
    }


async def main() -> None:
    svc = BenchmarkIntelligenceService()
    snap = BenchmarkIntelligenceSnapshotService(svc)
    results = {"sprint": "F04.6", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        print(f"F04.6 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        print(f"  done paridade={w.get('paridadeDelta')} parecer={w.get('parecerFinal')}", flush=True)

    ref = results["windows"]["7d"]
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qa") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "fonteWebPosto": False,
        "fonteF045": True,
        "cockpit": bool(ref.get("cockpit")),
        "paridadeZero": bool(qa.get("paridadeZero")),
        "semCrossTenant": bool(qa.get("semCrossTenant")),
        "semDuplicidade": bool(qa.get("semDuplicidade")),
        "semMetricasOrfas": bool(qa.get("semMetricasOrfas")),
        "aprovado": bool(ex.get("20_aprovadoF047")),
    }

    out = ROOT / "scripts" / "f04_6_benchmark_intelligence.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
