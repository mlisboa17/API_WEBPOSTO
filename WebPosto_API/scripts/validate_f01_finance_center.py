#!/usr/bin/env python3
"""Validação F01 — endpoints Centro Financeiro (8040 + API WebPosto)."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:8040"
DATA_INI = "2026-06-01"
DATA_FIM = "2026-06-07"
PERIOD = {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}


async def get(client: httpx.AsyncClient, path: str, empresa: str | None = None) -> dict:
    params = dict(PERIOD)
    if empresa is not None:
        params["empresaCodigo"] = empresa
    t0 = time.perf_counter()
    r = await client.get(f"{BASE}{path}", params=params, timeout=120)
    ms = round((time.perf_counter() - t0) * 1000, 1)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    return {"http": r.status_code, "ms": ms, "body": body}


async def main() -> int:
    results: dict = {"period": PERIOD, "checks": [], "performance": {}}
    async with httpx.AsyncClient() as client:
        # health
        try:
            await client.get(f"{BASE}/health", timeout=5)
        except Exception as exc:
            print(f"Backend indisponível em {BASE}: {exc}")
            return 1

        expense_cases = [
            ("Todos", None, None),
            ("11495", "11495", {11495}),
            ("5555", "5555", {5555}),
            ("11495,5555", "11495,5555", {11495, 5555}),
        ]
        for label, emp, expected_codes in expense_cases:
            resp = await get(client, "/api/v1/finance/center/expenses", emp)
            data = (resp["body"].get("data") or {})
            items = data.get("data") or []
            codes = {i.get("empresaCodigo") for i in items} if items else set()
            total = (data.get("resumo") or {}).get("totalRegistros", 0)
            ok = expected_codes is None or codes <= expected_codes
            if expected_codes and total:
                ok = ok and codes == expected_codes
            results["checks"].append(
                {"case": f"expenses_{label}", "ok": ok, "total": total, "empresas": sorted(codes)}
            )

        summary = await get(client, "/api/v1/finance/center/summary")
        payables = await get(client, "/api/v1/finance/center/payables")
        receivables = await get(client, "/api/v1/finance/center/receivables")
        bank = await get(client, "/api/v1/finance/center/bank-movements")
        cash = await get(client, "/api/v1/finance/center/cash")

        results["performance"] = {
            "summary_ms": summary["ms"],
            "payables_ms": payables["ms"],
            "receivables_ms": receivables["ms"],
            "bank_ms": bank["ms"],
            "cash_ms": cash["ms"],
        }

        sdata = summary["body"].get("data") or {}
        results["summary"] = {
            "despesas": sdata.get("despesasGerenciais"),
            "contasPagar": sdata.get("contasPagar"),
            "contasReceber": sdata.get("contasReceber"),
            "movimento": sdata.get("movimentoBancario", {}).get("totalRegistros"),
            "caixaTurnos": (sdata.get("caixa") or {}).get("turnos"),
            "warnings": sdata.get("warnings"),
            "has_totalFinanceiro": "totalFinanceiro" in sdata,
        }

        rec_total = (receivables["body"].get("data") or {}).get("total")
        bank_total = (bank["body"].get("data") or {}).get("paginacaoCompleta") or (bank["body"].get("data") or {}).get("resumo", {}).get("totalRegistros")
        cash_turnos = (cash["body"].get("data") or {}).get("turnos", {}).get("count")

        results["checks"].extend([
            {"case": "summary_http_200", "ok": summary["http"] == 200 and summary["body"].get("success")},
            {"case": "no_totalFinanceiro", "ok": not results["summary"]["has_totalFinanceiro"]},
            {"case": "receivables_11", "ok": rec_total == 11, "total": rec_total},
            {"case": "bank_movements", "ok": (bank_total or 0) >= 200, "registros": bank_total},
            {"case": "cash_21_turnos", "ok": cash_turnos == 21, "turnos": cash_turnos},
            {
                "case": "payables_buckets",
                "ok": payables["http"] == 200,
                "buckets": (payables["body"].get("data") or {}).get("buckets"),
            },
        ])

    out = ROOT / "scripts" / "validate_f01_results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(1 for c in results["checks"] if c.get("ok"))
    total = len(results["checks"])
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nPASS {passed}/{total} -> {out}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
