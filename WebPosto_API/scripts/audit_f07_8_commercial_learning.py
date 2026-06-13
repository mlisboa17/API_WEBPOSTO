#!/usr/bin/env python3
"""F07.8 — Commercial Learning audit (100% snapshots homologados)."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.commercial_learning_service import CommercialLearningService
from src.services.commercial_learning_snapshot_service import CommercialLearningSnapshotService

WINDOWS = {"7d": ("2026-06-01", "2026-06-07")}


async def audit_window(svc, snap, label, di, df) -> dict:
    t0 = time.perf_counter()
    resp = await svc.build(di, df, None)
    build_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not resp.success or not resp.data:
        return {"window": label, "error": str(resp.error), "buildMs": build_ms}
    data = resp.data
    await snap.collect(di, df, None, data)
    return {
        "window": label,
        "buildMs": build_ms,
        "fonte": data.get("fonte"),
        "executiveAnswers": data.get("executiveAnswers"),
        "qa": data.get("qa"),
        "parecerFinal": data.get("parecerFinal"),
        "recommendationEffectivenessEngine": data.get("recommendationEffectivenessEngine"),
        "responsiblePerformanceEngine": data.get("responsiblePerformanceEngine"),
        "branchLearningEngine": data.get("branchLearningEngine"),
        "recommendationCalibrationEngine": data.get("recommendationCalibrationEngine"),
        "outcomeLearningEngine": data.get("outcomeLearningEngine"),
        "executiveLearningReport": data.get("executiveLearningReport"),
        "cockpit": data.get("cockpit"),
        "dwLayer": data.get("dwLayer"),
    }


async def main() -> None:
    svc = CommercialLearningService()
    snap = CommercialLearningSnapshotService(svc)
    results = {"sprint": "F07.8", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
    out = ROOT / "scripts" / "f07_8_commercial_learning.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    w = results["windows"].get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    cal = w.get("recommendationCalibrationEngine") or {}
    ol = w.get("outcomeLearningEngine") or {}
    qa = w.get("qa") or {}
    print(f"F07.8 audit OK — buildMs={w.get('buildMs')} fonte={w.get('fonte', {}).get('modo')}")
    print(f"  ações avaliadas: {ex.get('1_acoesAvaliadas')}")
    print(f"  taxa acerto: {ex.get('16_taxaAcertoPct')}%")
    print(f"  calibradas: {cal.get('totalCalibradas')}")
    print(f"  sistema aprendeu: {ol.get('sistemaAprendendo')}")
    print(f"  QA auditável: {qa.get('motorAuditavel')}")
    print(f"  parecer: {w.get('parecerFinal')}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
