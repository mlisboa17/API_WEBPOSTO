#!/usr/bin/env python3
"""F03.4 — Operator Performance Intelligence audit (read-only, aditivo)."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from decimal import Decimal
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
from src.services.operator_performance_service import OperatorPerformanceService
from src.services.operator_performance_snapshot_service import OperatorPerformanceSnapshotService

WINDOWS = {
    "7d": ("2026-06-01", "2026-06-07"),
    "30d": ("2026-05-08", "2026-06-07"),
    "90d": ("2026-03-09", "2026-06-07"),
}


def _delta(a, b) -> float:
    return abs(float(a or 0) - float(b or 0))


async def audit_window(
    perf: OperatorPerformanceService,
    snap: OperatorPerformanceSnapshotService,
    label: str,
    di: str,
    df: str,
    include_windows: bool,
) -> dict:
    t0 = time.perf_counter()
    resp = await perf.build(di, df, None, include_windows=include_windows)
    build_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not resp.success or not resp.data:
        return {"window": label, "error": resp.error, "buildMs": build_ms}

    data = resp.data
    await snap.collect(di, df, None, include_windows)

    t1 = time.perf_counter()
    master = snap.get_master(di, df, None)
    hot_ms = round((time.perf_counter() - t1) * 1000, 1)

    payload = master.get("payload") or {}
    summary = data.get("summary") or {}
    snap_summary = (payload.get("summary") or {})

    parity_score = _delta(summary.get("operatorPerformanceScoreMedio"), snap_summary.get("operatorPerformanceScoreMedio"))
    parity_ops = _delta(
        summary.get("operadoresClassificados"),
        snap_summary.get("operadoresClassificados"),
    )

    op_slice = snap.get_slice("operators", di, df, None)
    snap_ops = (op_slice.get("data") or {}).get("total")
    live_ops = (data.get("operators") or {}).get("total")

    critical = data.get("criticalFocus") or {}
    op276 = critical.get("operador276288") or {}
    op294 = critical.get("operador294273") or {}
    pdv54193 = critical.get("pdv54193") or {}
    pdv15880 = critical.get("pdv15880") or {}

    return {
        "window": label,
        "periodo": {"inicio": di, "fim": df},
        "buildMs": build_ms,
        "snapshotHotMs": hot_ms,
        "summary": summary,
        "operators": data.get("operators"),
        "pdvs": data.get("pdvs"),
        "turns": data.get("turns"),
        "evolution": data.get("evolution"),
        "bestPractices": data.get("bestPractices"),
        "contextAttribution": data.get("contextAttribution"),
        "criticalFocus": critical,
        "formula": data.get("formula"),
        "performanceMs": data.get("performanceMs"),
        "qa": {
            "paridadeScoreMedio": parity_score,
            "paridadeOperadoresCount": parity_ops,
            "paridadeOpsTotal": _delta(live_ops, snap_ops),
            "paridadeOk": parity_score == 0.0 and parity_ops == 0.0 and _delta(live_ops, snap_ops) == 0.0,
            "snapshotHit": op_slice.get("hit"),
            "snapshotUnder500ms": hot_ms < 500,
        },
        "mandatoryCases": {
            "operador276288": {
                "score": op276.get("performanceScore"),
                "band": op276.get("performanceBand"),
                "critico": op276.get("performanceBand") == "Critico",
            },
            "operador294273": {
                "score": op294.get("performanceScore"),
                "band": op294.get("performanceBand"),
                "critico": op294.get("performanceBand") == "Critico",
            },
            "pdv54193": {
                "score": pdv54193.get("performanceScore"),
                "band": pdv54193.get("performanceBand"),
                "critico": pdv54193.get("performanceBand") == "Critico",
            },
            "pdv15880": {
                "score": pdv15880.get("performanceScore"),
                "band": pdv15880.get("performanceBand"),
                "critico": pdv15880.get("performanceBand") == "Critico",
            },
        },
    }


def executive_answers(w90: dict, w7: dict | None = None) -> dict:
    s = w90.get("summary") or {}
    ops = (w90.get("operators") or {}).get("todos") or (w90.get("operators") or {}).get("ranking") or []
    pdvs = (w90.get("pdvs") or {}).get("ranking") or []
    turns = (w90.get("turns") or {}).get("ranking") or []
    evo = w90.get("evolution") or {}
    crit = w90.get("criticalFocus") or {}
    qa = w90.get("qa") or {}
    snap_ms = w90.get("snapshotHotMs")

    best_op = s.get("melhorOperador") or {}
    worst_op = s.get("piorOperador") or {}
    best_pdv = s.get("melhorPdv") or {}
    worst_pdv = s.get("piorPdv") or {}
    best_turn = s.get("melhorTurno") or {}
    worst_turn = s.get("piorTurno") or {}

    devedores = sorted(
        [o for o in ops if float(o.get("saldoLedger") or 0) < 0],
        key=lambda x: float(x.get("saldoLedger") or 0),
    )
    credores = sorted(
        [o for o in ops if float(o.get("saldoLedger") or 0) > 0],
        key=lambda x: float(x.get("saldoLedger") or 0),
        reverse=True,
    )

    melhorando = (evo.get("melhorando") or [{}])[0] if evo.get("melhorando") else {}
    piorando = (evo.get("piorando") or [{}])[0] if evo.get("piorando") else {}

    base = {
        "1_melhorOperador": best_op.get("funcionarioCodigo"),
        "2_piorOperador": worst_op.get("funcionarioCodigo"),
        "3_maisMelhorou90d": melhorando.get("funcionarioCodigo"),
        "4_maisPiorou": piorando.get("funcionarioCodigo"),
        "5_maiorSaldoDevedor": (devedores[0] or {}).get("funcionarioCodigo") if devedores else None,
        "6_maiorSaldoCredor": (credores[0] or {}).get("funcionarioCodigo") if credores else None,
        "7_melhorPdv": best_pdv.get("pdvCodigo"),
        "8_piorPdv": worst_pdv.get("pdvCodigo"),
        "9_melhorTurno": best_turn.get("turnoCodigo") or best_turn.get("turno"),
        "10_piorTurno": worst_turn.get("turnoCodigo") or worst_turn.get("turno"),
        "11_operadoresCriticos": s.get("criticos"),
        "12_operadoresExcelentes": s.get("excelentes"),
        "13_scoreMedioRede": s.get("operatorPerformanceScoreMedio"),
        "14_melhoraOperacional90d": s.get("melhoraOperacional90d"),
        "15_pdv54193Critico": (crit.get("pdv54193") or {}).get("performanceBand") == "Critico",
        "16_pdv15880Critico": (crit.get("pdv15880") or {}).get("performanceBand") == "Critico",
        "17_operador276288Critico": (crit.get("operador276288") or {}).get("performanceBand") == "Critico",
        "18_operador294273Critico": (crit.get("operador294273") or {}).get("performanceBand") == "Critico",
        "19_snapshotSlaOk": snap_ms is not None and snap_ms < 500,
        "20_prontoF04": qa.get("paridadeOk") and qa.get("snapshotUnder500ms"),
    }
    ctx_exec = (w90.get("contextAttribution") or {}).get("executiveAnswers") or {}
    base.update(ctx_exec)
    return base


async def main() -> None:
    import os

    client = WebPostoClient(load_core_config())
    _ = client
    perf = OperatorPerformanceService()
    snap = OperatorPerformanceSnapshotService(perf, output_dir="snapshots/operator_performance_audit")

    only = os.environ.get("F03_4_WINDOW")
    windows = {only: WINDOWS[only]} if only and only in WINDOWS else WINDOWS

    results: dict[str, dict] = {}
    for label, (di, df) in windows.items():
        include_windows = label == "90d" or os.environ.get("F03_4_INCLUDE_WINDOWS") == "1"
        print(f"Auditing {label} {di}..{df} include_windows={include_windows}")
        results[label] = await audit_window(perf, snap, label, di, df, include_windows)

    w90 = results.get("90d") or results.get("30d") or results.get("7d") or {}
    w7 = results.get("7d")
    executive = executive_answers(w90, w7)

    qa_global = {
        "paridadeOk": all(r.get("qa", {}).get("paridadeOk") for r in results.values() if "qa" in r),
        "snapshotUnder500ms": all(
            r.get("qa", {}).get("snapshotUnder500ms") for r in results.values() if "qa" in r
        ),
        "classificacao100pct": (
            (w90.get("summary") or {}).get("operadoresClassificados", 0) > 0
            and (w90.get("summary") or {}).get("pdvsClassificados", 0) > 0
        ),
    }

    out = {
        "sprint": "F03.4",
        "windows": results,
        "qa": qa_global,
        "executiveAnswers": executive,
    }

    dest = ROOT / "scripts" / "f03_4_operator_performance.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Saved {dest}")
    print(json.dumps(executive, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
