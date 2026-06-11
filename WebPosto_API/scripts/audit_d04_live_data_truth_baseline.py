#!/usr/bin/env python3
"""D04 — Live Data Truth Baseline audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.live_data_truth_baseline_service import LiveDataTruthBaselineService
from src.services.live_data_truth_baseline_snapshot_service import LiveDataTruthBaselineSnapshotService

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
    qa = data.get("qaCertification") or {}
    return {
        "window": label,
        "buildMs": build_ms,
        "executiveAnswers": ex,
        "qaCertification": qa,
        "parecerFinal": data.get("parecerFinal"),
        "decisaoArquitetural": data.get("decisaoArquitetural"),
        "tokenConnectivityAudit": data.get("tokenConnectivityAudit"),
        "financialCoverageAudit": data.get("financialCoverageAudit"),
        "cashCoverageAudit": data.get("cashCoverageAudit"),
        "salesCoverageAudit": data.get("salesCoverageAudit"),
        "workforceCoverageAudit": data.get("workforceCoverageAudit"),
        "dataLineageConsistency": data.get("dataLineageConsistency"),
        "trustBaselineEngine": data.get("trustBaselineEngine"),
        "dataGovernance": data.get("dataGovernance"),
    }


async def main() -> None:
    svc = LiveDataTruthBaselineService()
    snap = LiveDataTruthBaselineSnapshotService(svc)
    results = {"sprint": "D04", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        print(f"D04 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        ex = w.get("executiveAnswers") or {}
        print(
            f"  done trust={ex.get('17_trustCorporativo')} "
            f"operacional={ex.get('1_integracoesOperacionais')} "
            f"parecer={w.get('parecerFinal')}",
            flush=True,
        )

    ref = results["windows"]["7d"]
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qaCertification") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "fonteWebPosto": False,
        "snapshotsOnly": True,
        "authorizedFiliais": ex.get("authorizedFiliais"),
        "operacionalMin5": bool((ex.get("1_integracoesOperacionais") or 0) >= 5),
        "corporateTrustMin75": bool((ex.get("17_trustCorporativo") or 0) >= 75),
        "paridadeCorporativaZero": bool((ex.get("13_paridadeCorporativa") or 999) <= 0.01),
        "qaAprovado": bool(qa.get("aprovado")),
        "certificado": bool(ex.get("20_prontoDecisoesAutomatizadas")),
    }

    out = ROOT / "scripts" / "d04_live_data_truth_baseline.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
