#!/usr/bin/env python3
"""Validação F01.3 — Inteligência Financeira + Health Score."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:8040"
PERIOD = {"dataInicial": "2026-06-01", "dataFinal": "2026-06-07"}
OUT = ROOT / "scripts" / "f01_3_validation_results.json"

CASES = [
    ("A_Todos", None),
    ("B_11495", "11495"),
    ("C_5555", "5555"),
    ("D_11495_5555", "11495,5555"),
    ("E_All", "11495,5256,5333,5555,5556,5557,5558,5559,5560,46433,74014"),
    ("F_Todos", None),
]


async def get_json(client: httpx.AsyncClient, path: str, empresa: str | None) -> dict:
    params = dict(PERIOD)
    if empresa:
        params["empresaCodigo"] = empresa
    t0 = time.perf_counter()
    r = await client.get(f"{BASE}{path}", params=params, timeout=180)
    ms = round((time.perf_counter() - t0) * 1000, 1)
    body = r.json() if "json" in (r.headers.get("content-type") or "") else {}
    return {"http": r.status_code, "ms": ms, "body": body}


def parity_classification(data: dict) -> bool:
    cls = data.get("classification") or {}
    total = Decimal(str(cls.get("totalValor") or 0))
    outros = Decimal(str(cls.get("outrosValor") or 0))
    identified = Decimal(str(cls.get("identifiedPercent") or 0))
    if total <= 0:
        return True
    calc_ident = (total - outros) / total * 100
    if abs(calc_ident - identified) >= Decimal("0.02"):
        return False
    v1_pct = cls.get("identifiedFromOutrosPercent")
    return v1_pct is not None and float(v1_pct) >= 80


async def main() -> int:
    results = {"period": PERIOD, "cases": [], "snapshot": {}, "classification": {}}
    async with httpx.AsyncClient() as client:
        try:
            await client.get(f"{BASE}/health", timeout=5)
        except Exception as exc:
            print(f"Backend indisponível: {exc}")
            return 1

        audit_path = ROOT / "scripts" / "expense_intelligence_audit.json"
        if audit_path.exists():
            results["classification"] = json.loads(audit_path.read_text(encoding="utf-8"))

        for label, emp in CASES:
            intel = await get_json(client, "/api/v1/finance/intelligence", emp)
            health = await get_json(client, "/api/v1/finance/intelligence/health-score", emp)
            idata = intel["body"].get("data") or {}
            hdata = health["body"].get("data") or {}
            ok = (
                intel["http"] == 200
                and health["http"] == 200
                and parity_classification(idata)
                and hdata.get("networkScore") is not None
            )
            results["cases"].append(
                {
                    "case": label,
                    "ok": ok,
                    "intel_ms": intel["ms"],
                    "health_ms": health["ms"],
                    "outrosPercent": (idata.get("classification") or {}).get("outrosPercent"),
                    "networkScore": hdata.get("networkScore"),
                }
            )

        await client.post(f"{BASE}/api/v1/finance/intelligence/refresh", params=PERIOD)
        await asyncio.sleep(15)
        t0 = time.perf_counter()
        snap = await client.get(f"{BASE}/api/v1/finance/intelligence/snapshot", params=PERIOD, timeout=60)
        hit_ms = round((time.perf_counter() - t0) * 1000, 1)
        snap_data = snap.json().get("data") or {}
        results["snapshot"] = {
            "fromSnapshot": snap_data.get("fromSnapshot"),
            "ms": hit_ms,
            "target_ok": hit_ms < 500,
        }

    results["pass"] = all(c["ok"] for c in results["cases"]) and results["snapshot"].get("fromSnapshot")
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if results["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
