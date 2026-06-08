#!/usr/bin/env python3
"""Validação P0.2 — multiselect despesas via API LOGOS 8040."""
from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8040"
DATA_INI = "2026-06-01"
DATA_FIM = "2026-06-07"
OUT = Path(__file__).resolve().parents[1] / "scripts" / "p0_2_validation_result.json"

FORBIDDEN_MULTI = {5256, 5333, 5556, 5557, 5559, 5560, 46433, 74014}


def fetch_all_expenses(client: httpx.Client, empresa: str | None) -> dict:
    params: dict = {"dataInicial": DATA_INI, "dataFinal": DATA_FIM, "page": 1, "limit": 500}
    if empresa:
        params["empresaCodigo"] = empresa
    rows: list = []
    page = 1
    total = None
    while page <= 40:
        params["page"] = page
        r = client.get(f"{BASE}/v1/financial/expenses", params=params, timeout=120)
        r.raise_for_status()
        body = r.json()
        data = (body.get("data") or {})
        batch = data.get("data") or []
        total = data.get("total", total)
        if not batch:
            break
        rows.extend(batch)
        if total is not None and len(rows) >= int(total):
            break
        if len(batch) < 500:
            break
        page += 1
    empresas = sorted({int(x["empresaCodigo"]) for x in rows if x.get("empresaCodigo") is not None})
    valor = sum(Decimal(str(x.get("valor") or 0)) for x in rows)
    return {
        "registros": len(rows),
        "total_api": total,
        "valorTotal": str(valor.quantize(Decimal("0.01"))),
        "empresaCodigos": empresas,
    }


def fetch_overview(client: httpx.Client, empresa: str | None) -> dict:
    params = {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}
    if empresa:
        params["empresaCodigo"] = empresa
    r = client.get(f"{BASE}/v1/financial/overview", params=params, timeout=120)
    r.raise_for_status()
    data = r.json().get("data") or {}
    cons = data.get("consolidado") or {}
    return {"total_despesas": cons.get("total_despesas"), "postos": len(data.get("postos") or [])}


def main() -> int:
    results: dict = {"periodo": {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}, "casos": {}}

    cases = [
        ("A_single_11495", "11495", {11495}, 71, "24676.71"),
        ("B_single_5555", "5555", {5555}, None, None),
        ("C_multi_11495_5555", "11495,5555", {11495, 5555}, None, None),
        ("D_todos", None, None, None, None),
    ]

    with httpx.Client() as client:
        health = client.get(f"{BASE}/health", timeout=10)
        if health.status_code != 200:
            print(f"Backend indisponível: {health.status_code}")
            return 1

        for name, emp, allowed, exp_count, exp_val in cases:
            exp = fetch_all_expenses(client, emp)
            ov = fetch_overview(client, emp)
            forbidden = [c for c in exp["empresaCodigos"] if c in FORBIDDEN_MULTI]
            ok = True
            notes: list[str] = []

            if name == "C_multi_11495_5555":
                ok = not forbidden and set(exp["empresaCodigos"]).issubset({11495, 5555})
                if forbidden:
                    notes.append(f"filiais proibidas: {forbidden}")
            elif allowed is not None:
                ok = set(exp["empresaCodigos"]) == allowed
                if not ok:
                    notes.append(f"empresas={exp['empresaCodigos']} esperado={sorted(allowed)}")
            if exp_count is not None and exp["registros"] != exp_count:
                notes.append(f"count {exp['registros']} != esperado {exp_count}")
            if exp_val is not None and exp["valorTotal"] != exp_val:
                notes.append(f"valor {exp['valorTotal']} != esperado {exp_val}")

            results["casos"][name] = {
                "empresaCodigo": emp,
                "expenses": exp,
                "overview": ov,
                "pass": ok,
                "notes": notes,
            }
            status = "PASS" if ok else "FAIL"
            print(f"{status} {name}: reg={exp['registros']} val={exp['valorTotal']} emp={exp['empresaCodigos']}")

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON: {OUT}")
    failed = sum(1 for c in results["casos"].values() if not c["pass"])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
