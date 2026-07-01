#!/usr/bin/env python3
"""RT-02 — Performance & operabilidade: trace, validação runtime e regressão."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PERIOD = "dataInicial=2026-06-01&dataFinal=2026-06-07"
OUT = ROOT / "scripts" / "rt02_performance_results.json"


def run() -> dict:
    from fastapi.testclient import TestClient
    from src.interfaces.http.app import create_app
    from src.services.financial_snapshot_service import FinancialSnapshotService
    from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService

    client = TestClient(create_app())
    snapshots = FinancialSnapshotService()
    key = snapshots.build_key("2026-06-01", "2026-06-07", None)

    if not snapshots.load_kind("financial_stock", key):
        async def _seed_stock() -> None:
            from src.gateway.shared_client import get_webposto_client

            overview = NetworkFinancialOverviewService(get_webposto_client())
            filters = FinancialOverviewFilters(data_inicial="2026-06-01", data_final="2026-06-07")
            resp = await overview.get_stock(filters, page=1, limit=500)
            if resp.success and resp.data:
                snapshots.save_kind("financial_stock", key, resp.data, source="rt02_homologation")

        try:
            asyncio.run(asyncio.wait_for(_seed_stock(), timeout=120))
        except Exception as exc:
            print("stock homologation seed skipped:", exc)

    endpoints = [
        ("health", "/health", 3.0),
        ("overview", f"/v1/financial/overview?{PERIOD}", 3.0),
        ("expenses", f"/v1/financial/expenses?{PERIOD}&page=1&limit=10", 3.0),
        ("stock", f"/v1/stock?{PERIOD}&page=1&limit=10", 8.0),
        ("sales", f"/v1/sales?{PERIOD}&page=1&limit=10", 9.0),
    ]
    regression = [
        ("f08_ops", f"/api/v1/financial/operations-center/cockpit?{PERIOD}", 3.0),
        ("f08_int", f"/api/v1/financial/intelligence-center/cockpit?{PERIOD}", 3.0),
        ("f07", f"/api/v1/non-fuel-products/cockpit?{PERIOD}", 3.0),
        ("fiscal", f"/api/v1/nfce-intelligence/cockpit?{PERIOD}", 3.0),
        ("executive", f"/api/v1/executive-scorecard/cockpit?{PERIOD}", 3.0),
    ]

    def probe(name: str, path: str, budget: float) -> dict:
        t0 = time.perf_counter()
        r = client.get(path, timeout=max(budget + 30, 60))
        elapsed = round(time.perf_counter() - t0, 2)
        body = r.json() if "json" in r.headers.get("content-type", "") else {}
        resilience = body.get("resilience") or {}
        return {
            "name": name,
            "path": path,
            "status": r.status_code,
            "elapsed_s": elapsed,
            "budget_s": budget,
            "ok": r.status_code < 400 and elapsed <= budget,
            "source": body.get("source") or resilience.get("source") or resilience.get("mode"),
            "mode": resilience.get("mode"),
            "reason": resilience.get("reason"),
            "has_lineage": bool(resilience.get("health") or resilience.get("snapshotKey")),
            "synthetic": bool((body.get("data") or {}).get("synthetic")) if isinstance(body.get("data"), dict) else False,
        }

    primary = [probe(n, p, b) for n, p, b in endpoints]
    reg = [probe(n, p, b) for n, p, b in regression]

    return {
        "generated_at": datetime.now().isoformat(),
        "period": "2026-06-01 → 2026-06-07",
        "primary": primary,
        "regression": reg,
        "summary": {
            "primary_ok": sum(1 for r in primary if r["ok"]),
            "primary_total": len(primary),
            "regression_ok": sum(1 for r in reg if r["ok"]),
            "regression_total": len(reg),
        },
    }


def main() -> int:
    payload = run()
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    for row in payload["primary"]:
        flag = "OK" if row["ok"] else "FAIL"
        print(flag, row["elapsed_s"], row["name"], row.get("mode") or row.get("source"))
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
