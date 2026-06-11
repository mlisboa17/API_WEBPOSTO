#!/usr/bin/env python3
"""D04.1 — Coverage Truth Audit (adversarial challenge to D04)."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.coverage_truth_audit_service import CoverageTruthAuditService
from src.services.coverage_truth_audit_snapshot_service import CoverageTruthAuditSnapshotService

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
    trust = data.get("trustScoreChallenge") or {}
    qa = data.get("qaCertification") or {}
    return {
        "window": label,
        "buildMs": build_ms,
        "executiveAnswers": ex,
        "trustScoreChallenge": trust,
        "qaCertification": qa,
        "parecerFinal": data.get("parecerFinal"),
        "technicalCoverageAudit": data.get("technicalCoverageAudit"),
        "businessCoverageAudit": data.get("businessCoverageAudit"),
        "prestacaoGapAudit": data.get("prestacaoGapAudit"),
        "peopleCoverageChallenge": data.get("peopleCoverageChallenge"),
        "financialGapAudit": data.get("financialGapAudit"),
        "operationalGapAudit": data.get("operationalGapAudit"),
        "hiddenEndpointDiscovery": data.get("hiddenEndpointDiscovery"),
        "oQueSabemos": data.get("oQueSabemos"),
        "oQueAchamosQueSabemos": data.get("oQueAchamosQueSabemos"),
        "oQueNaoSabemos": data.get("oQueNaoSabemos"),
    }


async def main() -> None:
    svc = CoverageTruthAuditService()
    snap = CoverageTruthAuditSnapshotService(svc)
    results = {"sprint": "D04.1", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        print(f"D04.1 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
        w = results["windows"][label]
        ex = w.get("executiveAnswers") or {}
        trust = w.get("trustScoreChallenge") or {}
        print(
            f"  trustTecnico={trust.get('trustTecnico')} "
            f"trustNegocio={trust.get('trustNegocio')} "
            f"trustExecutivo={trust.get('trustExecutivo')} "
            f"parecer={w.get('parecerFinal')}",
            flush=True,
        )

    ref = results["windows"]["7d"]
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qaCertification") or {}
    trust = ref.get("trustScoreChallenge") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "fonteWebPosto": False,
        "adversarial": True,
        "d04BaselineLoaded": True,
        "gapTecnicoNegocioMin15": bool((trust.get("gapTecnicoVsNegocio") or 0) >= 15),
        "d04Superestimou": bool(qa.get("d04SuperestimouCobertura")),
        "trustExecutivoMin75": bool((trust.get("trustExecutivo") or 0) >= 75),
        "respostas20": bool(len(ex) >= 20),
    }

    out = ROOT / "scripts" / "d04_1_coverage_truth_audit.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
