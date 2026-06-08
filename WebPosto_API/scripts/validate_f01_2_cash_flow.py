#!/usr/bin/env python3
"""Validação F01.2 — Fluxo de Caixa + paridade."""
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
OUT = ROOT / "scripts" / "f01_2_cash_flow_results.json"

CASES = [
    ("A_Todos", None),
    ("B_11495", "11495"),
    ("C_5555", "5555"),
    ("D_11495_5555", "11495,5555"),
    ("E_All", "11495,5256,5333,5555,5556,5557,5558,5559,5560,46433,74014"),
    ("F_Todos", None),
]


async def get_flow(client: httpx.AsyncClient, empresa: str | None) -> dict:
    params = dict(PERIOD)
    if empresa:
        params["empresaCodigo"] = empresa
    t0 = time.perf_counter()
    r = await client.get(f"{BASE}/api/v1/finance/cash-flow", params=params, timeout=180)
    ms = round((time.perf_counter() - t0) * 1000, 1)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    return {"http": r.status_code, "ms": ms, "data": body.get("data")}


def parity_daily_cards(data: dict) -> bool:
    daily = data.get("daily") or []
    cards = data.get("cards") or {}
    if not daily:
        return True
    ent = sum(Decimal(str(r.get("entradasPrevistas") or 0)) for r in daily)
    sai = sum(Decimal(str(r.get("saidasPrevistas") or 0)) for r in daily)
    net = ent - sai
    last_acum = Decimal(str(daily[-1].get("saldoAcumulado") or 0))
    return (
        ent == Decimal(str(cards.get("entradasPrevistas") or 0))
        and sai == Decimal(str(cards.get("saidasPrevistas") or 0))
        and net == Decimal(str(cards.get("saldoProjetado") or 0))
        and last_acum == Decimal(str(cards.get("saldoAcumulado") or 0))
    )


async def main() -> int:
    results = {"period": PERIOD, "cases": [], "snapshot": {}}
    async with httpx.AsyncClient() as client:
        try:
            await client.get(f"{BASE}/health", timeout=5)
        except Exception as exc:
            print(f"Backend indisponível: {exc}")
            return 1

        for label, emp in CASES:
            resp = await get_flow(client, emp)
            data = resp["data"] or {}
            ok = resp["http"] == 200 and parity_daily_cards(data)
            forbidden = set(data.get("forbiddenSourcesUsed") or [])
            sources = set(data.get("sources") or [])
            results["cases"].append(
                {
                    "case": label,
                    "ok": ok and "DESPESAS_REDE" not in sources and not forbidden,
                    "ms": resp["ms"],
                    "cards": data.get("cards"),
                    "daily_len": len(data.get("daily") or []),
                    "sources": data.get("sources"),
                }
            )

        await client.post(f"{BASE}/api/v1/finance/cash-flow/refresh", params=PERIOD)
        await asyncio.sleep(10)
        t0 = time.perf_counter()
        snap = await client.get(f"{BASE}/api/v1/finance/cash-flow/snapshot", params=PERIOD)
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
