#!/usr/bin/env python3
"""Sprint A03.6 — auditoria operacional automatizada."""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

BASE = "http://127.0.0.1:8040"
DATA_INI = "2026-06-03"
DATA_FIM = "2026-06-08"
EMPRESA_SINGLE = "11495"
EMPRESA_MULTI = "11495,5555"
TIMEOUT = 90


def get(path: str, params: dict | None = None) -> tuple[int, float, Any]:
    t0 = time.perf_counter()
    r = requests.get(f"{BASE}{path}", params=params or {}, timeout=TIMEOUT)
    elapsed = (time.perf_counter() - t0) * 1000
    try:
        body = r.json()
    except Exception:
        body = r.text[:500]
    return r.status_code, elapsed, body


def post(path: str, params: dict | None = None) -> tuple[int, float, Any]:
    t0 = time.perf_counter()
    r = requests.post(f"{BASE}{path}", params=params or {}, timeout=15)
    elapsed = (time.perf_counter() - t0) * 1000
    try:
        body = r.json()
    except Exception:
        body = r.text[:500]
    return r.status_code, elapsed, body


def sum_field(rows: list, field: str) -> float:
    total = 0.0
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in (field, field.lower(), field.upper()):
            if key in row:
                try:
                    total += float(str(row[key]).replace(",", "."))
                except (TypeError, ValueError):
                    pass
                break
    return total


def main() -> int:
    report: dict[str, Any] = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "base": BASE,
        "period": {"dataInicial": DATA_INI, "dataFinal": DATA_FIM},
    }

    # Health
    code, ms, body = get("/health")
    report["health"] = {"status": code, "ms": round(ms, 1)}

    base_params = {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}

    # Snapshots audit
    snapshots = {}
    for name, path in [
        ("executive", "/api/v1/executive/snapshot"),
        ("fuel", "/api/v1/fuel/snapshot"),
        ("financial", "/api/v1/financial/snapshot"),
    ]:
        for label, emp in [("single", EMPRESA_SINGLE), ("multi", EMPRESA_MULTI), ("all", None)]:
            params = {**base_params}
            if emp:
                params["empresaCodigo"] = emp
            code, ms, body = get(path, params)
            key = f"{name}_{label}"
            snapshots[key] = {
                "status": code,
                "ms": round(ms, 1),
                "fromSnapshot": body.get("fromSnapshot") if isinstance(body, dict) else None,
                "lastUpdated": body.get("lastUpdated") if isinstance(body, dict) else None,
                "hasData": bool(body.get("kpis") or body.get("fuel") or body.get("overview")) if isinstance(body, dict) else False,
            }
    report["snapshots"] = snapshots

    # Refresh triggers
    refresh = {}
    for name, path in [
        ("executive", "/api/v1/executive/refresh"),
        ("fuel", "/api/v1/fuel/refresh"),
        ("financial", "/api/v1/financial/refresh"),
    ]:
        code, ms, body = post(path, {**base_params, "empresaCodigo": EMPRESA_SINGLE})
        refresh[name] = {"status": code, "ms": round(ms, 1), "body": body}
    report["refresh"] = refresh

    # Performance benchmark
    perf = {}
    endpoints = [
        ("executive_snapshot", "/api/v1/executive/snapshot", base_params),
        ("fuel_snapshot", "/api/v1/fuel/snapshot", base_params),
        ("fuel_executive", "/api/v1/fuel/executive", {**base_params, "empresaCodigo": EMPRESA_MULTI}),
        ("kpis_multi", "/api/v1/kpis", {**base_params, "empresaCodigo": EMPRESA_MULTI}),
        ("expenses_multi", "/v1/financial/expenses", {**base_params, "empresaCodigo": EMPRESA_MULTI, "page": 1, "limit": 50}),
        ("accounts_multi", "/v1/financial/accounts-payable", {**base_params, "empresaCodigo": EMPRESA_MULTI, "page": 1, "limit": 50}),
        ("sales_multi", "/v1/sales", {**base_params, "empresaCodigo": EMPRESA_MULTI, "page": 1, "limit": 50}),
        ("stock_multi", "/v1/stock", {**base_params, "empresaCodigo": EMPRESA_MULTI, "page": 1, "limit": 50}),
        ("coverage", "/api/v1/network/coverage", {}),
    ]
    for name, path, params in endpoints:
        code, ms, body = get(path, params)
        perf[name] = {"status": code, "ms": round(ms, 1)}
    report["performance"] = perf

    # Multiselect comparison: single vs multi request count simulation
    _, ms_single, kpis_single = get("/api/v1/kpis", {**base_params, "empresaCodigo": EMPRESA_SINGLE})
    _, ms_multi, kpis_multi = get("/api/v1/kpis", {**base_params, "empresaCodigo": EMPRESA_MULTI})
    report["multiselect"] = {
        "kpis_single_ms": round(ms_single, 1),
        "kpis_multi_ms": round(ms_multi, 1),
        "kpis_multi_has_lineage": (kpis_multi.get("data") or {}).get("lineage") if isinstance(kpis_multi, dict) else None,
    }

    # Financial totals audit
    totals = {}
    for name, path, value_fields in [
        ("expenses", "/v1/financial/expenses", ["valor", "valorTotal", "valorDespesa"]),
        ("accounts", "/v1/financial/accounts-payable", ["valor", "valorTitulo", "valorTotal"]),
        ("sales", "/v1/sales", ["valorTotal", "valor", "total"]),
        ("stock", "/v1/stock", ["quantidade", "estoque", "saldo"]),
    ]:
        code, ms, body = get(path, {**base_params, "empresaCodigo": EMPRESA_SINGLE, "page": 1, "limit": 500})
        rows = []
        if isinstance(body, dict):
            data = body.get("data")
            if isinstance(data, dict):
                rows = data.get("data") or data.get("resultados") or []
            elif isinstance(data, list):
                rows = data
        page_total = len(rows) if isinstance(rows, list) else 0
        api_total = None
        if isinstance(body, dict) and isinstance(body.get("data"), dict):
            api_total = body["data"].get("total")
        summed = 0.0
        field_used = None
        for f in value_fields:
            s = sum_field(rows if isinstance(rows, list) else [], f)
            if s > 0:
                summed = s
                field_used = f
                break
        totals[name] = {
            "status": code,
            "rows_on_page": page_total,
            "api_total": api_total,
            "autosoma_field": field_used,
            "autosoma": round(summed, 2),
            "divergence": None,
        }
    report["totals"] = totals

    # Fuel audit
    fuel = {}
    _, ms, fe = get("/api/v1/fuel/executive", {**base_params, "empresaCodigo": EMPRESA_SINGLE})
    _, ms2, fs = get("/api/v1/sales/fuel-summary", {**base_params, "empresaCodigo": EMPRESA_SINGLE})
    fuel_exec = fe.get("data") if isinstance(fe, dict) else {}
    fuel_summary = fs if isinstance(fs, list) else []
    products_with_code_only = 0
    combustiveis = fuel_exec.get("combustiveis") or []
    for item in combustiveis:
        name_val = item.get("combustivel") or item.get("combustivelDisplay") or ""
        if str(name_val).isdigit():
            products_with_code_only += 1
    fuel["fuel_executive_ms"] = round(ms, 1)
    fuel["fuel_summary_ms"] = round(ms2, 1)
    fuel["litros_lmc"] = fuel_exec.get("litrosTotal") or (fuel_exec.get("kpis") or {}).get("litrosVendidos")
    fuel["litros_vendidos_summary"] = sum(float(str(i.get("litros") or 0).replace(",", ".")) for i in fuel_summary if isinstance(i, dict))
    fuel["products_code_only"] = products_with_code_only
    fuel["combustiveis_count"] = len(combustiveis)
    report["fuel"] = fuel

    # Coverage score
    _, _, cov = get("/api/v1/network/coverage")
    report["coverage"] = {
        "indiceCoberturaRede": cov.get("indiceCoberturaRede") if isinstance(cov, dict) else None,
        "filiaisComCombustivel": cov.get("filiaisComCombustivel") if isinstance(cov, dict) else None,
        "filiaisComDados": cov.get("filiaisComDados") if isinstance(cov, dict) else None,
    }

    # Snapshot files on disk
    snap_dirs = ["snapshots/executive", "snapshots/fuel", "snapshots/financial"]
    disk = {}
    for d in snap_dirs:
        p = Path(d)
        if p.exists():
            files = list(p.glob("*.json"))
            disk[d] = {"count": len(files), "files": [f.name for f in files[:5]]}
        else:
            disk[d] = {"count": 0}
    report["disk_snapshots"] = disk

    out = Path("scripts/audit_a03_6_results.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
