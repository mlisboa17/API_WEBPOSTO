#!/usr/bin/env python3
"""Validação F01.2 direta no serviço (sem depender de reload uvicorn)."""
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
from src.services.cash_flow_snapshot_service import CashFlowSnapshotService
from src.services.corporate_cash_flow_service import CorporateCashFlowService, FORBIDDEN_SOURCES
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.network_financial_overview_service import NetworkFinancialOverviewService

DATA_INI = "2026-06-01"
DATA_FIM = "2026-06-07"


def parity(data: dict) -> bool:
    daily = data.get("daily") or []
    cards = data.get("cards") or {}
    if not daily:
        return False
    ent = sum(Decimal(str(r.get("entradasPrevistas") or 0)) for r in daily)
    sai = sum(Decimal(str(r.get("saidasPrevistas") or 0)) for r in daily)
    net = ent - sai
    last = Decimal(str(daily[-1].get("saldoAcumulado") or 0))
    return (
        ent == Decimal(str(cards.get("entradasPrevistas") or 0))
        and sai == Decimal(str(cards.get("saidasPrevistas") or 0))
        and net == Decimal(str(cards.get("saldoProjetado") or 0))
        and last == Decimal(str(cards.get("saldoAcumulado") or 0))
    )


async def main() -> int:
    client = WebPostoClient()
    overview = NetworkFinancialOverviewService(client)
    fc = CorporateFinanceCenterService(overview)
    flow_svc = CorporateCashFlowService(fc)
    snap_svc = CashFlowSnapshotService(CorporateCashFlowService(fc))

    results = {"period": {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}, "cases": []}
    all_codes = "11495,5256,5333,5555,5556,5557,5558,5559,5560,46433,74014"
    for label, emp in [
        ("A_Todos", None),
        ("B_11495", "11495"),
        ("C_5555", "5555"),
        ("D_11495_5555", "11495,5555"),
        ("E_All", all_codes),
        ("F_Todos", None),
    ]:
        t0 = time.perf_counter()
        filters = build_finance_center_filters(DATA_INI, DATA_FIM, emp)
        resp = await flow_svc.build(filters, emp)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        data = resp.data or {}
        ok = resp.success and parity(data) and not (FORBIDDEN_SOURCES & set(data.get("sources") or []))
        results["cases"].append(
            {
                "case": label,
                "ok": ok,
                "ms": ms,
                "cards": data.get("cards"),
                "daily_len": len(data.get("daily") or []),
            }
        )

    t0 = time.perf_counter()
    miss = snap_svc.get_snapshot(DATA_INI, DATA_FIM, None)
    miss_ms = round((time.perf_counter() - t0) * 1000, 1)
    await snap_svc.collect(DATA_INI, DATA_FIM, None)
    t0 = time.perf_counter()
    hit = snap_svc.get_snapshot(DATA_INI, DATA_FIM, None)
    hit_ms = round((time.perf_counter() - t0) * 1000, 1)
    results["snapshot"] = {
        "miss_ms": miss_ms,
        "miss": miss.get("fromSnapshot"),
        "hit_ms": hit_ms,
        "hit": hit.get("fromSnapshot"),
        "target_ok": hit_ms < 500,
    }
    results["pass"] = all(c["ok"] for c in results["cases"]) and hit.get("fromSnapshot")
    out = ROOT / "scripts" / "f01_2_cash_flow_direct.json"
    api_out = ROOT / "scripts" / "f01_2_cash_flow_results.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    api_out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if results["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
