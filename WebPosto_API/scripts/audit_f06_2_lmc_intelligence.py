#!/usr/bin/env python3
"""F06.2 — LMC Intelligence audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.lmc_intelligence_service import LmcIntelligenceService
from src.services.lmc_intelligence_snapshot_service import LmcIntelligenceSnapshotService

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
        "lmcCatalogEngine": data.get("lmcCatalogEngine"),
        "fuelReconciliationEngine": data.get("fuelReconciliationEngine"),
        "lossSurplusEngine": data.get("lossSurplusEngine"),
        "tankIntelligence": data.get("tankIntelligence"),
        "pumpIntelligence": data.get("pumpIntelligence"),
        "lmcExecutiveIntelligence": data.get("lmcExecutiveIntelligence"),
        "dwLayer": data.get("dwLayer"),
    }


async def main() -> None:
    svc = LmcIntelligenceService()
    snap = LmcIntelligenceSnapshotService(svc)
    results = {"sprint": "F06.2", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        print(f"F06.2 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        ex = w.get("executiveAnswers") or {}
        print(
            f"  done vendido={ex.get('2_totalVendido')} risco={ex.get('13_maiorRisco')} "
            f"parecer={w.get('parecerFinal')}",
            flush=True,
        )

    ref = results["windows"]["7d"]
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qa") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "fonteWebPostoLive": False,
        "snapshotsHomologados": bool(qa.get("snapshotsHomologados")),
        "motorAuditavel": bool(qa.get("motorAuditavel")),
        "lineageCompleto": bool(qa.get("lineageCompleto")),
        "semCrossTenant": bool(qa.get("semCrossTenant")),
        "semCalculoSemOrigem": bool(qa.get("semCalculoSemOrigem")),
        "semPerdaSemEvidencia": bool(qa.get("semPerdaSemEvidencia")),
        "semReconciliacaoSemLineage": bool(qa.get("semReconciliacaoSemLineage")),
        "lmcIntelligenceViavel": bool(ex.get("19_lmcIntelligenceViavel")),
        "aprovadoF063": bool(ex.get("20_aprovadoF063")),
    }

    out = ROOT / "scripts" / "f06_2_lmc_intelligence.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
