"""Read-only executive value discovery across real snapshots."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "snapshots"
TENANTS = {"5555": "AP CASA CAIADA", "11495": "POSTO VIP", "74014": "POSTO DOZE FILIAL II"}
PERIOD = ("2026-06-05", "2026-07-04")


def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def expense_category_spikes(tenant: str) -> list[dict]:
    path = SNAP / "discovery_expense" / f"discovery_expense_{tenant}_{tenant}_{PERIOD[0]}_{PERIOD[1]}.json"
    data = load_json(path)
    if not data:
        return []
    cur = data.get("expense_data", {}).get("current_expenses") or []
    base = data.get("expense_data", {}).get("baseline_expenses") or []
    cur_by = Counter()
    base_by = Counter()
    cur_amt = defaultdict(float)
    base_amt = defaultdict(float)
    for row in cur:
        cat = str(row.get("planoConta") or "SEM_CATEGORIA")
        cur_by[cat] += 1
        cur_amt[cat] += float(row.get("valor") or 0)
    for row in base:
        cat = str(row.get("planoConta") or "SEM_CATEGORIA")
        base_by[cat] += 1
        base_amt[cat] += float(row.get("valor") or 0)
    out = []
    for cat in set(cur_by) | set(base_by):
        cc, bc = cur_by[cat], base_by[cat]
        ca, ba = cur_amt[cat], base_amt[cat]
        if cc < 3 or ca < 500:
            continue
        delta = ca - ba
        pct = ((cc - bc) / bc * 100) if bc else None
        if delta >= 2000 and (pct is None or pct >= 20):
            out.append({
                "tenant": tenant,
                "problem_class": "EXPENSE_CATEGORY_SPIKE",
                "category": cat,
                "current_value": round(ca, 2),
                "baseline_value": round(ba, 2),
                "absolute_delta": round(delta, 2),
                "percent_delta": round(pct, 1) if pct is not None else None,
                "count_current": cc,
                "count_baseline": bc,
                "money_type": "ESTIMATED",
            })
    return sorted(out, key=lambda x: x["absolute_delta"], reverse=True)


def receivable_overdue(tenant: str) -> dict | None:
    path = SNAP / "discovery_receivable" / f"discovery_receivable_{tenant}_{tenant}_{PERIOD[0]}_{PERIOD[1]}.json"
    data = load_json(path)
    if not data:
        return None
    rows = data.get("receivable_data", {}).get("receivable_rows") or []
    overdue = [r for r in rows if r.get("pendente") and r.get("dataVencimento")]
    gap = 0.0
    ref = date.fromisoformat(PERIOD[1])
    overdue_count = 0
    for r in overdue:
        try:
            due = date.fromisoformat(str(r["dataVencimento"])[:10])
        except ValueError:
            continue
        if (ref - due).days >= 7:
            overdue_count += 1
            gap += float(r.get("valor") or 0)
    if gap < 1500:
        return None
    return {
        "tenant": tenant,
        "problem_class": "OVERDUE_RECEIVABLE",
        "current_value": round(gap, 2),
        "baseline_value": 0,
        "absolute_delta": round(gap, 2),
        "overdue_count": overdue_count,
        "money_type": "AT_RISK",
    }


def fuel_revenue_shift(tenant: str) -> dict | None:
    path = SNAP / "discovery_fuel" / f"discovery_fuel_{tenant}_{tenant}_{PERIOD[0]}_{PERIOD[1]}.json"
    data = load_json(path)
    if not data:
        return None
    fuel = data.get("fuel_data") or {}
    comps = fuel.get("product_comparisons") or []
    total_delta = 0.0
    drops = []
    for c in comps:
        cur = float(c.get("current_liters") or c.get("current_value") or 0)
        prev = float(c.get("previous_liters") or c.get("previous_value") or 0)
        delta_val = float(c.get("revenue_delta") or c.get("value_delta") or (cur - prev))
        if prev > 0 and delta_val <= -3000:
            drops.append(c)
            total_delta += abs(delta_val)
    if not drops:
        return None
    return {
        "tenant": tenant,
        "problem_class": "FUEL_REVENUE_DROP",
        "absolute_delta": round(total_delta, 2),
        "products": [d.get("product") or d.get("combustivel") for d in drops[:3]],
        "money_type": "ESTIMATED",
    }


def financial_overview_margin(tenant: str) -> dict | None:
    path = SNAP / "financial" / f"financial_overview_{PERIOD[0]}_{PERIOD[1]}_5555_11495_74014.json"
    data = load_json(path)
    if not data:
        return None
    rows = data.get("data") or data.get("resultados") or []
    if isinstance(data, dict) and "snapshot" in data:
        rows = (data.get("snapshot") or {}).get("data") or []
    for row in rows:
        code = str(row.get("empresaCodigo") or row.get("filial") or "")
        if code != tenant:
            continue
        vendas = float(row.get("vendas_combustivel") or row.get("total_vendas") or 0)
        despesas = float(row.get("total_despesas") or 0)
        if vendas <= 0:
            return None
        margin = (vendas - despesas) / vendas * 100
        return {
            "tenant": tenant,
            "problem_class": "MARGIN_SNAPSHOT",
            "vendas": round(vendas, 2),
            "despesas": round(despesas, 2),
            "margin_pct": round(margin, 2),
            "money_type": "ESTIMATED",
        }
    return None


def main() -> None:
    opportunities: list[dict] = []
    for tenant in TENANTS:
        opportunities.extend(expense_category_spikes(tenant))
        rec = receivable_overdue(tenant)
        if rec:
            opportunities.append(rec)
        fuel = fuel_revenue_shift(tenant)
        if fuel:
            opportunities.append(fuel)
        margin = financial_overview_margin(tenant)
        if margin:
            opportunities.append(margin)

    # cross-tenant: same category spike in multiple tenants
    by_cat: dict[str, list] = defaultdict(list)
    for op in opportunities:
        if op.get("problem_class") == "EXPENSE_CATEGORY_SPIKE":
            by_cat[op["category"]].append(op)

    print(json.dumps({
        "period": PERIOD,
        "tenants": TENANTS,
        "opportunities": opportunities,
        "cross_tenant_categories": {k: v for k, v in by_cat.items() if len(v) >= 2},
        "top_by_delta": sorted(opportunities, key=lambda x: x.get("absolute_delta", 0), reverse=True)[:10],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
