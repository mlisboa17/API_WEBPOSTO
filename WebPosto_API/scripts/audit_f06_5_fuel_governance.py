#!/usr/bin/env python3
"""F06.5 — Fuel Governance audit."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.fuel_governance_service import FuelGovernanceService
from src.services.fuel_governance_snapshot_service import FuelGovernanceSnapshotService

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
        "executiveAnswers": data.get("executiveAnswers") or {},
        "qa": data.get("qa") or {},
        "parecerFinal": data.get("parecerFinal"),
        "processoOperacionalSuficiente": data.get("processoOperacionalSuficiente"),
        "cockpit": data.get("cockpit"),
        "lmcComplianceAudit": data.get("lmcComplianceAudit"),
        "routineAdherenceAudit": data.get("routineAdherenceAudit"),
        "operationalDisciplineAudit": data.get("operationalDisciplineAudit"),
        "delayAnalysisEngine": data.get("delayAnalysisEngine"),
        "branchComplianceRanking": data.get("branchComplianceRanking"),
        "fuelGovernanceIntelligence": data.get("fuelGovernanceIntelligence"),
        "dwLayer": data.get("dwLayer"),
    }


async def main() -> None:
    svc = FuelGovernanceService()
    snap = FuelGovernanceSnapshotService(svc)
    results = {"sprint": "F06.5", "windows": {}}
    for label, (di, df) in WINDOWS.items():
        results["windows"][label] = await audit_window(svc, snap, label, di, df)
    out = ROOT / "scripts" / "f06_5_fuel_governance_and_lmc_compliance.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    w = results["windows"].get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    print(f"F06.5 audit OK — buildMs={w.get('buildMs')}")
    print(f"  conformidade: {ex.get('3_taxaConformidadeLmc')}%")
    print(f"  dias com/sem LMC: {ex.get('1_diasComLmc')}/{ex.get('2_diasSemLmc')}")
    print(f"  rotina diária: {ex.get('10_lmcPreenchidoDiariamente')}")
    print(f"  parecer: {w.get('parecerFinal')}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
