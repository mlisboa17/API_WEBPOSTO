#!/usr/bin/env python3
"""Validação F01.3 direta (serviço, sem HTTP)."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gateway.webposto_client import WebPostoClient
from src.services.analytics_multiselect import build_finance_center_filters
from src.services.corporate_cash_flow_service import CorporateCashFlowService
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.finance_intelligence_snapshot_service import FinanceIntelligenceSnapshotService
from src.services.financial_health_score_service import FinancialHealthScoreService
from src.services.financial_intelligence_service import FinancialIntelligenceService
from src.services.network_financial_overview_service import NetworkFinancialOverviewService

DATA_INI, DATA_FIM = "2026-06-01", "2026-06-07"
OUT = ROOT / "scripts" / "f01_3_validation_results.json"

CASES = [
    ("A_Todos", None),
    ("B_11495", "11495"),
    ("C_5555", "5555"),
    ("D_11495_5555", "11495,5555"),
    ("E_All", "11495,5256,5333,5555,5556,5557,5558,5559,5560,46433,74014"),
    ("F_Todos", None),
]


def parity(cls: dict, require_outros_goal: bool = False) -> bool:
    total = Decimal(str(cls.get("totalValor") or 0))
    outros = Decimal(str(cls.get("outrosValor") or 0))
    identified = Decimal(str(cls.get("identifiedPercent") or 0))
    if total <= 0:
        return True
    calc = (total - outros) / total * 100
    if abs(calc - identified) >= Decimal("0.02"):
        return False
    if require_outros_goal and float(cls.get("identifiedFromOutrosPercent") or 0) < 80:
        return False
    return True


async def main() -> int:
    client = WebPostoClient()
    fc = CorporateFinanceCenterService(NetworkFinancialOverviewService(client))
    flow = CorporateCashFlowService(fc)
    intel = FinancialIntelligenceService(fc, flow)
    health = FinancialHealthScoreService(fc, flow, intel)
    snap = FinanceIntelligenceSnapshotService(intel, health)

    audit = {}
    ap = ROOT / "scripts" / "expense_intelligence_audit.json"
    if ap.exists():
        audit = json.loads(ap.read_text(encoding="utf-8"))

    results = {"period": {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}, "cases": [], "classification": audit, "snapshot": {}}

    for label, emp in CASES:
        t0 = time.perf_counter()
        filters = build_finance_center_filters(DATA_INI, DATA_FIM, emp)
        ir = await intel.build(filters, emp)
        hr = await health.build(filters, emp)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        idata = ir.data or {}
        hdata = hr.data or {}
        cls = idata.get("classification") or {}
        ok = ir.success and hr.success and parity(cls, require_outros_goal=(label == "A_Todos")) and hdata.get("networkScore") is not None
        results["cases"].append(
            {
                "case": label,
                "ok": ok,
                "ms": ms,
                "outrosPercent": cls.get("outrosPercent"),
                "identifiedFromOutrosPercent": cls.get("identifiedFromOutrosPercent"),
                "networkScore": hdata.get("networkScore"),
            }
        )

    await snap.collect(DATA_INI, DATA_FIM, None)
    t0 = time.perf_counter()
    hit = snap.get_snapshot(DATA_INI, DATA_FIM, None)
    hit_ms = round((time.perf_counter() - t0) * 1000, 1)
    results["snapshot"] = {"fromSnapshot": hit.get("fromSnapshot"), "hit_ms": hit_ms, "target_ok": hit_ms < 500}

    results["pass"] = all(c["ok"] for c in results["cases"]) and hit.get("fromSnapshot")
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if results["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
