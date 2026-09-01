"""Deeper read-only probe for unexplored executive value."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "snapshots"
TENANTS = ["5555", "11495", "74014"]
PERIOD = ("2026-06-05", "2026-07-04")


def load(path: Path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def expense_top_categories_excluding_vale(tenant: str) -> list[dict]:
    path = SNAP / "discovery_expense" / f"discovery_expense_{tenant}_{tenant}_{PERIOD[0]}_{PERIOD[1]}.json"
    data = load(path)
    if not data:
        return []
    cur = data.get("expense_data", {}).get("current_expenses") or []
    base = data.get("expense_data", {}).get("baseline_expenses") or []
    cur_amt = defaultdict(float)
    base_amt = defaultdict(float)
    cur_cnt = Counter()
    base_cnt = Counter()
    for row in cur:
        cat = str(row.get("planoConta") or "SEM")
        if "vale" in cat.lower() and "consolida" in cat.lower():
            continue
        cur_amt[cat] += float(row.get("valor") or 0)
        cur_cnt[cat] += 1
    for row in base:
        cat = str(row.get("planoConta") or "SEM")
        if "vale" in cat.lower() and "consolida" in cat.lower():
            continue
        base_amt[cat] += float(row.get("valor") or 0)
        base_cnt[cat] += 1
    out = []
    for cat in cur_amt:
        delta = cur_amt[cat] - base_amt.get(cat, 0)
        if delta >= 1500 and cur_cnt[cat] >= 2:
            out.append({
                "tenant": tenant,
                "category": cat,
                "delta": round(delta, 2),
                "current": round(cur_amt[cat], 2),
                "baseline": round(base_amt.get(cat, 0), 2),
                "count_current": cur_cnt[cat],
                "count_baseline": base_cnt.get(cat, 0),
            })
    return sorted(out, key=lambda x: x["delta"], reverse=True)


def non_fuel_sales_signal() -> list[dict]:
    path = SNAP / "non_fuel_products" / f"nonfuel_products_{PERIOD[0]}_{PERIOD[1]}_all.json"
    data = load(path)
    if not data:
        return []
    # structure varies - try common keys
    payload = data.get("data") or data.get("snapshot") or data
    items = []
    if isinstance(payload, dict):
        for key in ("products", "items", "ranking", "top_products"):
            if isinstance(payload.get(key), list):
                items = payload[key]
                break
    out = []
    for row in items if isinstance(items, list) else []:
        tenant = str(row.get("empresaCodigo") or row.get("tenant_id") or "")
        if tenant not in TENANTS:
            continue
        drop = float(row.get("variation_percent") or row.get("delta_pct") or 0)
        value = float(row.get("revenue") or row.get("valor") or row.get("total") or 0)
        if drop <= -25 and value >= 1000:
            out.append({"tenant": tenant, "product": row.get("descricao") or row.get("label"), "drop_pct": drop, "value": value})
    return out


def stock_capital_signal() -> list[dict]:
    path = SNAP / "financial" / f"financial_overview_{PERIOD[0]}_{PERIOD[1]}_5555_11495_74014.json"
    data = load(path)
    if not data:
        return []
    return [{"note": "financial_overview present", "keys": list(data.keys())[:8]}]


def receivable_concentration(tenant: str) -> dict | None:
    path = SNAP / "discovery_receivable" / f"discovery_receivable_{tenant}_{tenant}_{PERIOD[0]}_{PERIOD[1]}.json"
    data = load(path)
    if not data:
        return None
    rows = data.get("receivable_data", {}).get("receivable_rows") or []
    by_client = defaultdict(float)
    overdue_by_client = defaultdict(float)
    for r in rows:
        if not r.get("pendente"):
            continue
        client = str(r.get("nomeCliente") or "SEM")
        val = float(r.get("valor") or 0)
        by_client[client] += val
        overdue_by_client[client] += val
    if not by_client:
        return None
    total = sum(by_client.values())
    top_client, top_val = max(by_client.items(), key=lambda x: x[1])
    share = top_val / total if total else 0
    if share >= 0.35 and top_val >= 800:
        return {
            "tenant": tenant,
            "problem_class": "RECEIVABLE_CONCENTRATION",
            "top_client": top_client,
            "top_value": round(top_val, 2),
            "total_pending": round(total, 2),
            "share": round(share, 3),
            "money_type": "AT_RISK",
        }
    return None


def main():
    results = {
        "expense_ex_vale": {t: expense_top_categories_excluding_vale(t) for t in TENANTS},
        "receivable_concentration": [receivable_concentration(t) for t in TENANTS],
        "non_fuel": non_fuel_sales_signal(),
        "stock": stock_capital_signal(),
    }
    results["receivable_concentration"] = [x for x in results["receivable_concentration"] if x]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
