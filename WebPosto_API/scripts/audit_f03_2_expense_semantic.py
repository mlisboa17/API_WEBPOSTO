#!/usr/bin/env python3
"""F03.2 — Expense Semantic Intelligence audit (read-only)."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from src.core.config import load_core_config
from src.gateway.webposto_client import WebPostoClient
from src.services.expense_lineage_service import ExpenseLineageService, _norm_text
from src.services.expense_semantic_service import EXPENSE_NATURES, ExpenseSemanticService
from src.services.expense_semantic_snapshot_service import ExpenseSemanticSnapshotService
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService

WINDOWS = {
    "7d": ("2026-06-01", "2026-06-07"),
    "30d": ("2026-05-08", "2026-06-07"),
    "90d": ("2026-03-09", "2026-06-07"),
}

QA_CASES = [
    {"label": "BOBINA TERMICA", "termo": "BOBINA", "empresaCodigo": 5555, "filial": "AP CASA CAIADA"},
    {"label": "VALE FUNCIONARIO", "termo": "VALE", "empresaCodigo": None, "filial": None},
    {"label": "TROCO", "termo": "TROCO", "empresaCodigo": None, "filial": None},
    {"label": "FUNDO DE CAIXA", "termo": "FUNDO", "empresaCodigo": None, "filial": None},
]


def _money_sum(rows: list[dict]) -> Decimal:
    return sum(Decimal(str(r.get("valor") or 0)) for r in rows).quantize(Decimal("0.01"))


async def audit_window(
    overview: NetworkFinancialOverviewService,
    semantic: ExpenseSemanticService,
    lineage: ExpenseLineageService,
    label: str,
    di: str,
    df: str,
) -> dict:
    filters = FinancialOverviewFilters(data_inicial=di, data_final=df)
    t0 = time.time()
    payload = await semantic.build_semantic_payload(overview, filters, lineage)
    rows = payload.get("rows") or []
    summary = payload.get("summary") or {}
    elapsed = round(time.time() - t0, 1)

    by_nature_sub: dict[str, dict[str, int]] = {n: {} for n in EXPENSE_NATURES}
    for r in rows:
        nat = str(r.get("expenseNature") or "?")
        sub = str(r.get("expenseSubNature") or "?")
        by_nature_sub.setdefault(nat, {})
        by_nature_sub[nat][sub] = by_nature_sub[nat].get(sub, 0) + 1

    top_sub = summary.get("topSubNatures") or []

    return {
        "window": label,
        "periodo": {"inicio": di, "fim": df},
        "elapsedSec": elapsed,
        "summary": summary,
        "cards": payload.get("cards"),
        "byNatureSubNature": by_nature_sub,
        "topSubNatures": top_sub,
        "paridade": {
            "screenRecords": len(rows),
            "classifiedRecords": summary.get("classifiedRecords"),
            "delta": summary.get("unclassifiedRecords", 0),
        },
    }


async def qa_cases(
    overview: NetworkFinancialOverviewService,
    semantic: ExpenseSemanticService,
    lineage: ExpenseLineageService,
) -> list[dict]:
    filters = FinancialOverviewFilters(data_inicial="2026-06-01", data_final="2026-06-08")
    payload = await semantic.build_semantic_payload(overview, filters, lineage)
    rows = payload.get("rows") or []
    api_resp = await overview.get_financial_expenses(filters, page=1, limit=99999)
    api_data = (api_resp.data or {}).get("data") or []
    api_total = _money_sum(api_data)
    screen_total = _money_sum(rows)

    cases_out = []
    for case in QA_CASES:
        hits = [r for r in rows if case["termo"] in _norm_text(r.get("descricao") or r.get("planoConta") or "")]
        if case.get("empresaCodigo"):
            hits = [r for r in hits if r.get("empresaCodigo") == case["empresaCodigo"]]
        sample = hits[0] if hits else {}
        cases_out.append(
            {
                "label": case["label"],
                "ocorrencias": len(hits),
                "expenseNature": sample.get("expenseNature"),
                "expenseSubNature": sample.get("expenseSubNature"),
                "semanticConfidence": sample.get("semanticConfidence"),
                "amostra": {
                    "empresaCodigo": sample.get("empresaCodigo"),
                    "data": sample.get("data"),
                    "valor": sample.get("valor"),
                    "descricao": sample.get("descricao"),
                }
                if sample
                else None,
            }
        )

    return {
        "cases": cases_out,
        "paridadeValor": float(abs(api_total - screen_total)),
        "paridadeOk": abs(api_total - screen_total) == Decimal("0"),
        "apiRecords": len(api_data),
        "screenRecords": len(rows),
    }


async def snapshot_qa(snapshot: ExpenseSemanticSnapshotService, overview: NetworkFinancialOverviewService) -> dict:
    filters = FinancialOverviewFilters(data_inicial="2026-06-01", data_final="2026-06-07")
    t0 = time.time()
    payload1, stale1, hit1 = await snapshot.get_or_collect(filters)
    miss_ms = round((time.time() - t0) * 1000, 1)

    t1 = time.time()
    slice_resp = snapshot.get_slice("2026-06-01", "2026-06-07")
    hit_ms = round((time.time() - t1) * 1000, 1)

    payload2, stale2, hit2 = await snapshot.get_or_collect(filters)

    return {
        "firstCollectMs": miss_ms,
        "hitReadMs": hit_ms,
        "hitOnSecondCall": hit2,
        "staleOnHit": stale2,
        "ttlSeconds": slice_resp.get("ttlSeconds"),
        "snapshotKey": slice_resp.get("snapshotKey"),
        "keyPrefix": "expenses:semantic",
        "hitUnder500ms": hit_ms < 500,
    }


async def main() -> None:
    cfg = load_core_config()
    client = WebPostoClient(cfg)
    overview = NetworkFinancialOverviewService(client)
    semantic = ExpenseSemanticService()
    lineage = ExpenseLineageService()
    snapshot = ExpenseSemanticSnapshotService(overview, semantic, lineage)

    out: dict = {"windows": {}, "qa": {}, "snapshot": {}, "executiveAnswers": {}}
    for label, (di, df) in WINDOWS.items():
        print(f"Auditing {label}...")
        out["windows"][label] = await audit_window(overview, semantic, lineage, label, di, df)

    print("QA mandatory cases...")
    out["qa"] = await qa_cases(overview, semantic, lineage)
    print("Snapshot QA...")
    out["snapshot"] = await snapshot_qa(snapshot, overview)

    s90 = out["windows"]["90d"]["summary"]
    pct = s90.get("pctByNature") or {}
    out["executiveAnswers"] = {
        "1_totalClassified": s90.get("classifiedRecords"),
        "2_pctFinanceira": pct.get("DESPESA_FINANCEIRA"),
        "3_pctOperacional": pct.get("DESPESA_OPERACIONAL"),
        "4_pctMovimentacao": pct.get("MOVIMENTACAO_CAIXA"),
        "5_pctAdiantamento": pct.get("ADIANTAMENTO"),
        "6_pctAjuste": pct.get("AJUSTE_OPERACIONAL"),
        "7_impactoFinanceiroPct": s90.get("pctFinancialImpact"),
        "8_top20SubNatures": s90.get("topSubNatures"),
        "9_principalFinanceira": (s90.get("topSubNatures") or [["?", 0]])[0],
        "10_unclassified": s90.get("unclassifiedRecords"),
        "11_avgConfidence": s90.get("avgSemanticConfidence"),
        "12_classificationPct": s90.get("classificationPct"),
        "13_paridadeOk": out["qa"].get("paridadeOk"),
        "14_snapshotHit500ms": out["snapshot"].get("hitUnder500ms"),
    }

    dest = ROOT / "scripts" / "f03_2_expense_semantic.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"JSON -> {dest}")


if __name__ == "__main__":
    asyncio.run(main())
