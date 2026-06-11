#!/usr/bin/env python3
"""D05 — Executive Coverage Recovery audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.executive_coverage_recovery_service import ExecutiveCoverageRecoveryService
from src.services.executive_coverage_recovery_snapshot_service import ExecutiveCoverageRecoverySnapshotService

WINDOWS = {"7d": ("2026-06-01", "2026-06-07")}


async def audit_window(svc, snap, label, di, df) -> dict:
    t0 = time.perf_counter()
    resp = await svc.build(di, df, None)
    build_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not resp.success or not resp.data:
        return {"window": label, "error": str(resp.error), "buildMs": build_ms}
    data = resp.data
    await snap.collect(di, df, None, data)
    rec = data.get("executiveCoverageRecalculation") or {}
    depois = rec.get("depois") or {}
    return {
        "window": label,
        "buildMs": build_ms,
        "executiveAnswers": data.get("executiveAnswers"),
        "executiveCoverageRecalculation": rec,
        "executiveTrustGovernance": data.get("executiveTrustGovernance"),
        "qaCertification": data.get("qaCertification"),
        "parecerFinal": data.get("parecerFinal"),
        "officialGoalDiscovery": data.get("officialGoalDiscovery"),
        "officialParticipationDiscovery": data.get("officialParticipationDiscovery"),
        "officialProductivityDiscovery": data.get("officialProductivityDiscovery"),
        "prestacaoRecovery": data.get("prestacaoRecovery"),
        "lmcRecovery": data.get("lmcRecovery"),
        "movimentoCaixaRecovery": data.get("movimentoCaixaRecovery"),
        "gapsDelta": data.get("gapsDelta"),
    }


async def main() -> None:
    svc = ExecutiveCoverageRecoveryService()
    snap = ExecutiveCoverageRecoverySnapshotService(svc)
    results = {"sprint": "D05", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        print(f"D05 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        dep = (w.get("executiveCoverageRecalculation") or {}).get("depois") or {}
        print(
            f"  trustNegocio={dep.get('trustNegocio')} trustExecutivo={dep.get('trustExecutivo')} "
            f"parecer={w.get('parecerFinal')}",
            flush=True,
        )

    ref = results["windows"]["7d"]
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qaCertification") or {}
    dep = (ref.get("executiveCoverageRecalculation") or {}).get("depois") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "fonteWebPosto": False,
        "trustNegocioGt80": bool((dep.get("trustNegocio") or 0) > 80),
        "trustExecutivoGt70": bool((dep.get("trustExecutivo") or 0) > 70),
        "qaAprovado": bool(qa.get("aprovado")),
        "f051Liberado": bool(ex.get("20_f051Liberado")),
    }

    out = ROOT / "scripts" / "d05_executive_coverage_recovery.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
