#!/usr/bin/env python3
"""F06.1 — NFCE Intelligence audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.nfce_intelligence_service import NfceIntelligenceService
from src.services.nfce_intelligence_snapshot_service import NfceIntelligenceSnapshotService

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
        "nfceCatalogEngine": data.get("nfceCatalogEngine"),
        "nfceLineageEngine": data.get("nfceLineageEngine"),
        "nfceReconciliationEngine": data.get("nfceReconciliationEngine"),
        "nfceRiskEngine": data.get("nfceRiskEngine"),
        "nfceAnomalyEngine": data.get("nfceAnomalyEngine"),
        "nfceExecutiveIntelligence": data.get("nfceExecutiveIntelligence"),
        "dwLayer": data.get("dwLayer"),
    }


async def main() -> None:
    svc = NfceIntelligenceService()
    snap = NfceIntelligenceSnapshotService(svc)
    results = {"sprint": "F06.1", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        print(f"F06.1 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        ex = w.get("executiveAnswers") or {}
        print(
            f"  done total={ex.get('1_totalNfceHomologadas')} risco={ex.get('9_riscoMaximo')} "
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
        "cockpitAprovado": bool(ex.get("18_cockpitAprovado")),
        "fiscalIntelligenceViavel": bool(ex.get("19_fiscalIntelligenceViavel")),
        "aprovadoF062": bool(ex.get("20_aprovadoF062")),
    }

    out = ROOT / "scripts" / "f06_1_nfce_intelligence.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
