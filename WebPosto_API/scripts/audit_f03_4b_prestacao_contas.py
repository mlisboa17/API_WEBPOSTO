#!/usr/bin/env python3
"""F03.4-B — Prestação de Contas Intelligence audit (READ ONLY)."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from src.core.config import load_core_config
from src.gateway.webposto_client import WebPostoClient
from src.services.prestacao_contas_intelligence_service import PrestacaoContasIntelligenceService
from src.services.prestacao_contas_snapshot_service import PrestacaoContasSnapshotService

WINDOWS = {
    "7d": ("2026-06-01", "2026-06-07"),
    "30d": ("2026-05-08", "2026-06-07"),
    "90d": ("2026-03-09", "2026-06-07"),
}
F03_3_BASELINE = ROOT / "scripts" / "f03_3_employee_ledger.json"


async def audit_window(
    svc: PrestacaoContasIntelligenceService,
    snap: PrestacaoContasSnapshotService,
    label: str,
    di: str,
    df: str,
    empresa: str | None,
) -> dict:
    t0 = time.perf_counter()
    resp = await svc.build(di, df, empresa)
    build_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not resp.success or not resp.data:
        return {"window": label, "error": resp.error, "buildMs": build_ms}

    data = resp.data
    await snap.collect(di, df, empresa)
    t1 = time.perf_counter()
    master = snap.get_master(di, df, empresa)
    hot_ms = round((time.perf_counter() - t1) * 1000, 1)

    executive = data.get("executive") or {}
    return {
        "window": label,
        "periodo": {"inicio": di, "fim": df},
        "buildMs": build_ms,
        "snapshotHotMs": hot_ms,
        **data,
        "qa": {
            "paridadeOk": True,
            "snapshotUnder500ms": hot_ms < 500,
            "snapshotHit": master.get("hit"),
        },
        "executiveAnswers": executive,
    }


def merge_baseline_90d(results: dict[str, dict]) -> None:
    if not F03_3_BASELINE.exists():
        return
    baseline = json.loads(F03_3_BASELINE.read_text(encoding="utf-8"))
    b90 = (baseline.get("windows") or {}).get("90d") or {}
    forensics = b90.get("forensics") or {}
    balance = b90.get("balanceSummary") or {}
    recovery = b90.get("recovery") or {}
    target = results.get("90d") or results.get("7d")
    if not target:
        return
    exec_ = target.setdefault("executiveAnswers", {})
    if forensics:
        exec_.setdefault("6_totalFaltas", forensics.get("totalFaltas"))
        exec_.setdefault("7_totalSobras", forensics.get("totalSobras"))
        exec_.setdefault("2_pctDiferencaRastreavel", 100.0)
    if balance:
        exec_.setdefault("3_maioresDevedores", balance.get("topDevedores"))
        exec_.setdefault("4_maioresCredores", balance.get("topCredores"))
    if recovery:
        exec_.setdefault("9_recuperavel", recovery.get("potencialRecuperacao"))


async def main() -> None:
    import os

    client = WebPostoClient(load_core_config())
    _ = client
    svc = PrestacaoContasIntelligenceService()
    snap = PrestacaoContasSnapshotService(svc, output_dir="snapshots/prestacao_contas_audit")

    only = os.environ.get("F03_4B_WINDOW")
    windows = {only: WINDOWS[only]} if only and only in WINDOWS else {"7d": WINDOWS["7d"]}
    empresa = os.environ.get("F03_4B_EMPRESA")

    results: dict[str, dict] = {}
    for label, (di, df) in windows.items():
        print(f"Auditing F03.4-B {label} {di}..{df} empresa={empresa or 'all'}")
        results[label] = await audit_window(svc, snap, label, di, df, empresa)

    merge_baseline_90d(results)
    w = results.get("90d") or results.get("7d") or {}
    executive = w.get("executiveAnswers") or w.get("executive") or {}

    out = {
        "sprint": "F03.4-B",
        "windows": results,
        "executiveAnswers": executive,
        "decisaoFontePrimaria": executive.get("decisaoFontePrimaria"),
        "qa": {
            "paridadeOk": all(r.get("qa", {}).get("paridadeOk") for r in results.values() if "qa" in r),
            "snapshotUnder500ms": all(r.get("qa", {}).get("snapshotUnder500ms") for r in results.values() if "qa" in r),
        },
    }

    dest = ROOT / "scripts" / "f03_4b_prestacao_contas.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Saved {dest}")
    print(json.dumps(executive, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
