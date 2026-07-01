#!/usr/bin/env python3
"""RT-00 — Inventário operacional read-only (telas, APIs, snapshots)."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:8050"
PERIOD = "dataInicial=2026-06-01&dataFinal=2026-06-07"
TIMEOUT = 8

VIEWS = [
    "executiveWorkspace", "executiveScorecard", "actionCenter", "goalsCampaign", "dashboard",
    "expenses", "accounts", "cashFlow", "cashOperations", "financeCenter",
    "financialOperationsCenter", "financialIntelligence", "financialMonitoring", "financialOperations",
    "sales", "stock", "fuels", "fuelExecutive", "lmcIntelligence", "fuelGovernance",
    "nonFuelProducts", "commercialCopilot", "commercialExecution", "commercialLearning",
    "nfceIntelligence", "fiscalReconciliation", "fiscalIntelligence", "administration",
    "executive", "operatorPerformance", "peopleIntelligence", "peopleRoi", "operationRoi",
    "managementAction", "benchmark", "corporateHub", "executiveDecision", "executiveCopilot",
    "recommendations", "learning",
]

API_ENDPOINTS = [
    ("GET", "/health"),
    ("GET", "/app/financial"),
    ("GET", f"/v1/financial/overview?{PERIOD}"),
    ("GET", f"/v1/financial/expenses?{PERIOD}&page=1&limit=10"),
    ("GET", f"/v1/sales?{PERIOD}&page=1&limit=10"),
    ("GET", f"/v1/stock?{PERIOD}&page=1&limit=10"),
    ("GET", f"/v1/financial/accounts-payable?{PERIOD}&page=1&limit=10"),
    ("GET", f"/api/v1/financial/operations-center/cockpit?{PERIOD}"),
    ("GET", f"/api/v1/financial/intelligence-center/cockpit?{PERIOD}"),
    ("GET", "/api/v1/financial/snapshot-health/inventory"),
    ("GET", "/api/v1/financial/operations/scheduler/status"),
    ("GET", "/api/v1/admin/circuit-breaker/status"),
    ("GET", f"/api/v1/finance/cash-flow/snapshot?{PERIOD}"),
    ("GET", f"/api/v1/cash/operations/summary?{PERIOD}"),
    ("GET", f"/api/v1/finance/center/snapshot?{PERIOD}"),
    ("GET", f"/api/v1/non-fuel-products/cockpit?{PERIOD}"),
    ("GET", f"/api/v1/fuel-governance/cockpit?{PERIOD}"),
    ("GET", f"/api/v1/nfce-intelligence/cockpit?{PERIOD}"),
    ("GET", f"/api/v1/fiscal-reconciliation/cockpit?{PERIOD}"),
    ("GET", f"/api/v1/fiscal-intelligence/cockpit?{PERIOD}"),
    ("GET", f"/api/v1/lmc-intelligence/cockpit?{PERIOD}"),
    ("GET", f"/api/v1/commercial-execution/cockpit?{PERIOD}"),
    ("GET", f"/api/v1/commercial-copilot/cockpit?{PERIOD}"),
    ("GET", f"/api/v1/commercial-learning/cockpit?{PERIOD}"),
    ("GET", f"/api/v1/executive-scorecard/cockpit?{PERIOD}"),
    ("GET", f"/api/v1/performance/summary?{PERIOD}"),
    ("GET", f"/api/v1/operator-intelligence/cockpit?{PERIOD}"),
    ("GET", f"/api/v1/sales/fuel-summary?{PERIOD}"),
    ("GET", f"/api/v1/fuel/executive?{PERIOD}"),
    ("GET", f"/api/v1/action-center/cockpit?{PERIOD}"),
    ("GET", f"/api/v1/executive-copilot/cockpit?{PERIOD}"),
    ("GET", f"/api/v1/benchmark/cockpit?{PERIOD}"),
]


def probe(method: str, path: str, *, timeout: float = TIMEOUT) -> dict:
    url = f"{BASE}{path}" if path.startswith("/") else path
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            elapsed = round(time.perf_counter() - t0, 2)
            parsed = None
            try:
                parsed = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                parsed = None
            return {
                "path": path,
                "status": resp.status,
                "elapsed_s": elapsed,
                "ok": 200 <= resp.status < 300,
                "bytes": len(body),
                "json": isinstance(parsed, dict),
                "success": parsed.get("success") if isinstance(parsed, dict) else None,
                "source": parsed.get("source") if isinstance(parsed, dict) else None,
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        elapsed = round(time.perf_counter() - t0, 2)
        return {"path": path, "status": exc.code, "elapsed_s": elapsed, "ok": False, "error": str(exc.reason)}
    except Exception as exc:  # noqa: BLE001
        elapsed = round(time.perf_counter() - t0, 2)
        kind = "timeout" if "timed out" in str(exc).lower() else type(exc).__name__
        return {"path": path, "status": 0, "elapsed_s": elapsed, "ok": False, "error": kind}


def scan_snapshots() -> list[dict]:
    snap_root = ROOT / "snapshots"
    items: list[dict] = []
    if not snap_root.is_dir():
        return items
    for file_path in sorted(snap_root.rglob("*.json")):
        if file_path.name.startswith("_"):
            continue
        rel = file_path.relative_to(snap_root)
        kind = rel.parts[0] if rel.parts else "root"
        stat = file_path.stat()
        age_h = round((time.time() - stat.st_mtime) / 3600, 1)
        size_kb = round(stat.st_size / 1024, 1)
        items.append({"kind": kind, "file": str(rel), "age_hours": age_h, "size_kb": size_kb})
    return items


def classify_api(row: dict) -> str:
    if row.get("ok") and row.get("elapsed_s", 99) <= 22:
        return "FUNCIONA"
    if row.get("ok") and row.get("elapsed_s", 0) > 22:
        return "PARCIAL"
    if row.get("status") in {404, 405}:
        return "NAO_ACESSIVEL"
    if row.get("error") == "timeout":
        return "PARCIAL"
    return "NAO_RESPONDE"


def main() -> dict:
    screens = []
    for view in VIEWS:
        row = probe("GET", f"/app/financial?view={view}")
        row["view"] = view
        row["url"] = f"/app/financial?view={view}"
        if row["ok"] and row.get("bytes", 0) > 1000:
            row["classification"] = "OPERACIONAL" if row["elapsed_s"] < 5 else "PARCIAL"
        elif row["ok"]:
            row["classification"] = "PARCIAL"
        else:
            row["classification"] = "QUEBRADA"
        screens.append(row)

    apis = []
    for method, path in API_ENDPOINTS:
        row = probe(method, path)
        row["classification"] = classify_api(row)
        apis.append(row)

    snapshots = scan_snapshots()
    by_kind: dict[str, int] = {}
    for snap in snapshots:
        by_kind[snap["kind"]] = by_kind.get(snap["kind"], 0) + 1

    out = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base": BASE,
        "screens": screens,
        "apis": apis,
        "snapshots": snapshots,
        "snapshot_kinds": by_kind,
        "summary": {
            "screens_total": len(screens),
            "screens_shell_ok": sum(1 for s in screens if s["ok"]),
            "apis_total": len(apis),
            "apis_funciona": sum(1 for a in apis if a["classification"] == "FUNCIONA"),
            "apis_parcial": sum(1 for a in apis if a["classification"] == "PARCIAL"),
            "apis_broken": sum(1 for a in apis if a["classification"] in {"NAO_RESPONDE", "NAO_ACESSIVEL"}),
            "snapshot_files": len(snapshots),
            "snapshot_kinds_count": len(by_kind),
        },
    }
    out_path = ROOT / "scripts" / "rt00_inventory_data.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out["summary"], indent=2))
    return out


if __name__ == "__main__":
    main()
