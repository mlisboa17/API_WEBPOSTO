#!/usr/bin/env python3
"""Validação F01 — direto no serviço (sem depender de reload do uvicorn)."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gateway.webposto_client import WebPostoClient
from src.services.analytics_multiselect import build_finance_center_filters
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.network_financial_overview_service import NetworkFinancialOverviewService

DATA_INI = "2026-06-01"
DATA_FIM = "2026-06-07"


async def main() -> int:
    client = WebPostoClient()
    overview = NetworkFinancialOverviewService(client)
    service = CorporateFinanceCenterService(overview)
    results: dict = {"period": {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}, "checks": [], "performance": {}}

    expense_cases = [
        ("Todos", None, None),
        ("11495", "11495", {11495}),
        ("5555", "5555", {5555}),
        ("11495,5555", "11495,5555", {11495, 5555}),
    ]
    for label, emp, expected_codes in expense_cases:
        t0 = time.perf_counter()
        filters = build_finance_center_filters(DATA_INI, DATA_FIM, emp)
        resp = await service.get_expenses(filters, emp, page=1, limit=500)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        resumo = (resp.data or {}).get("resumo") or {}
        items = (resp.data or {}).get("data") or []
        codes = {i.get("empresaCodigo") for i in items}
        total = resumo.get("totalRegistros", 0)
        ok = resp.success
        if expected_codes is not None and total:
            ok = ok and codes <= expected_codes and codes == expected_codes
        if expected_codes is None:
            ok = ok and total >= 400
        results["checks"].append({"case": f"expenses_{label}", "ok": ok, "total": total, "ms": ms, "empresas": sorted(codes)})

    t0 = time.perf_counter()
    summary_resp = await service.get_summary(
        build_finance_center_filters(DATA_INI, DATA_FIM, None),
        None,
    )
    results["performance"]["summary_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    pay_resp = await service.get_payables(build_finance_center_filters(DATA_INI, DATA_FIM, None), None)
    rec_resp = await service.get_receivables(build_finance_center_filters(DATA_INI, DATA_FIM, None), None)
    bank_resp = await service.get_bank_movements(build_finance_center_filters(DATA_INI, DATA_FIM, None), None)
    cash_resp = await service.get_cash(build_finance_center_filters(DATA_INI, DATA_FIM, None), None)

    sdata = summary_resp.data or {}
    rec_total = (rec_resp.data or {}).get("total")
    bank_regs = (bank_resp.data or {}).get("paginacaoCompleta")
    cash_turnos = ((cash_resp.data or {}).get("turnos") or {}).get("count")

    results["summary"] = {
        "despesas": sdata.get("despesasGerenciais"),
        "contasPagar": sdata.get("contasPagar"),
        "contasReceber": sdata.get("contasReceber"),
        "movimentoRegistros": (sdata.get("movimentoBancario") or {}).get("totalRegistros"),
        "caixaTurnos": (sdata.get("caixa") or {}).get("turnos"),
        "warnings": sdata.get("warnings"),
        "snapshotKey": sdata.get("snapshotKey"),
    }

    results["checks"].extend([
        {"case": "summary_success", "ok": summary_resp.success},
        {"case": "no_totalFinanceiro", "ok": "totalFinanceiro" not in sdata},
        {"case": "receivables_11", "ok": rec_total == 11, "total": rec_total},
        {"case": "bank_movements_200plus", "ok": (bank_regs or 0) >= 200, "registros": bank_regs},
        {"case": "cash_21_turnos", "ok": cash_turnos == 21, "turnos": cash_turnos},
        {
            "case": "payables_buckets",
            "ok": pay_resp.success and (pay_resp.data or {}).get("buckets") is not None,
            "buckets": (pay_resp.data or {}).get("buckets"),
        },
    ])

    exp = await service.get_expenses(build_finance_center_filters(DATA_INI, DATA_FIM, None), None, limit=5)
    items = (exp.data or {}).get("data") or []
    results["checks"].append(
        {"case": "expenses_categoriaLogos", "ok": all(i.get("categoriaLogos") for i in items), "sample": items[:2]}
    )

    out = ROOT / "scripts" / "validate_f01_results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    passed = sum(1 for c in results["checks"] if c.get("ok"))
    total = len(results["checks"])
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    print(f"\nPASS {passed}/{total} -> {out}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
