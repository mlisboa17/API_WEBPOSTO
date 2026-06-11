#!/usr/bin/env python3
"""F04.0 — Operator Performance & Sales Intelligence audit."""
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

from src.services.operator_sales_intelligence_service import OperatorSalesIntelligenceService
from src.services.operator_sales_intelligence_snapshot_service import OperatorSalesIntelligenceSnapshotService

WINDOWS = {
    "7d": ("2026-06-01", "2026-06-07"),
    "30d": ("2026-05-08", "2026-06-07"),
    "90d": ("2026-03-09", "2026-06-07"),
}


async def audit_window(
    intel: OperatorSalesIntelligenceService,
    snap: OperatorSalesIntelligenceSnapshotService,
    label: str,
    di: str,
    df: str,
) -> dict:
    t0 = time.perf_counter()
    resp = await intel.build(di, df, None)
    build_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not resp.success or not resp.data:
        return {"window": label, "error": str(resp.error), "buildMs": build_ms}

    data = resp.data
    await snap.collect(di, df, None, data)
    master = snap.get_master(di, df, None)
    snap_payload = master.get("payload") or {}

    live_par = (data.get("executiveAnswers") or {}).get("paridadeDelta", 999)
    snap_par = (snap_payload.get("executiveAnswers") or {}).get("paridadeDelta", 999)
    parity_ok = abs(float(live_par or 0) - float(snap_par or 0)) <= 0.01 and float(live_par or 999) <= 0.01

    return {
        "window": label,
        "periodo": {"inicio": di, "fim": df},
        "buildMs": build_ms,
        "dimEmployee": {
            "total": (data.get("dimEmployee") or {}).get("total"),
            "ativos": (data.get("dimEmployee") or {}).get("ativos"),
            "nominalizacaoPct": (data.get("dimEmployee") or {}).get("nominalizacaoPct"),
        },
        "salesOperators": len((data.get("salesPerformance") or {}).get("operators") or []),
        "productivityBands": (data.get("productivityEngine") or {}).get("bands"),
        "discountTotal": (data.get("discountIntelligence") or {}).get("totalDesconto"),
        "riskCriticos": len(
            [r for r in (data.get("operatorRiskEngine") or []) if r.get("riskBand") == "Critico"]
        ),
        "executiveAnswers": data.get("executiveAnswers"),
        "qa": data.get("qa"),
        "parecerFinal": data.get("parecerFinal"),
        "paridadeDelta": live_par,
        "paridadeOk": parity_ok,
        "cockpit": data.get("cockpit"),
    }


async def main() -> None:
    only = __import__("os").environ.get("F04_WINDOW")
    windows = {only: WINDOWS[only]} if only and only in WINDOWS else {"7d": WINDOWS["7d"]}

    intel = OperatorSalesIntelligenceService()
    snap = OperatorSalesIntelligenceSnapshotService(intel)
    results: dict = {"sprint": "F04.0", "windows": {}}

    for label, (di, df) in windows.items():
        print(f"F04.0 audit {label} {di}..{df}", flush=True)
        results["windows"][label] = await audit_window(intel, snap, label, di, df)
        print(f"  done paridade={results['windows'][label].get('paridadeDelta')} parecer={results['windows'][label].get('parecerFinal')}", flush=True)

    ref = results["windows"].get("7d") or next(iter(results["windows"].values()), {})
    ex = ref.get("executiveAnswers") or {}
    qa = ref.get("qa") or {}
    results["executiveAnswers"] = ex
    results["parecerFinal"] = ref.get("parecerFinal")
    results["acceptance"] = {
        "dimEmployee": bool(qa.get("dimEmployeeOk")),
        "nominalizacao": bool(qa.get("nominalizacaoCompleta")),
        "paridadeZero": bool(qa.get("paridadeZero")),
        "aprovado": bool(ex.get("20_aprovadoF041")),
    }

    out = ROOT / "scripts" / "f04_0_operator_intelligence.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    print(ref.get("parecerFinal", ""))


if __name__ == "__main__":
    asyncio.run(main())
