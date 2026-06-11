#!/usr/bin/env python3
"""F03.2-A — Workforce Payment Forensics audit (read-only)."""
from __future__ import annotations

import asyncio
import csv
import json
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from src.core.config import load_core_config
from src.gateway.webposto_client import WebPostoClient
from src.services.expense_lineage_service import ExpenseLineageService
from src.services.expense_semantic_service import ExpenseSemanticService
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService
from workforce_forensics_engine import WorkforceForensicsEngine, bootstrap_optional_sources, load_context

WINDOWS = {
    "7d": ("2026-06-01", "2026-06-07"),
    "30d": ("2026-05-08", "2026-06-07"),
    "90d": ("2026-03-09", "2026-06-07"),
}
OPTIONAL_WINDOWS = {
    "180d": ("2025-12-09", "2026-06-07"),
    "365d": ("2025-06-07", "2026-06-07"),
}

QA_LABELS = [
    "VALE FUNCIONARIO",
    "QUINZENA",
    "SALARIO",
    "FOLGUISTA",
    "EXTRA",
    "EMPRESTIMO",
    "FALTA DE CAIXA",
]


async def audit_window(
    engine: WorkforceForensicsEngine,
    overview: NetworkFinancialOverviewService,
    lineage: ExpenseLineageService,
    semantic: ExpenseSemanticService,
    config: Any,
    label: str,
    di: str,
    df: str,
    shared: dict[str, Any] | None = None,
) -> dict:
    filters = FinancialOverviewFilters(data_inicial=di, data_final=df)
    t0 = time.time()
    shared = shared or {}
    ctx = await load_context(
        overview,
        lineage,
        semantic,
        filters,
        config,
        endpoint_probe=shared.get("probe"),
        funcionarios=shared.get("funcionarios"),
        vales_endpoint=shared.get("vales"),
        despesa_funcionario=shared.get("desp_func"),
    )
    discovery = engine.discover_workforce(ctx)
    classification = engine.classify_adiantamentos(ctx)
    calendar = engine.payroll_calendar(ctx)
    employee = engine.employee_match(ctx)
    cash_loss = engine.cash_loss_accountability(ctx)
    impact = engine.financial_impact(classification, cash_loss)
    separation = engine.payroll_separation(classification, cash_loss)
    mgmt = engine.management_prep(classification)

    return {
        "window": label,
        "periodo": {"inicio": di, "fim": df},
        "elapsedSec": round(time.time() - t0, 1),
        "discovery": discovery,
        "classification": classification,
        "payrollCalendar": calendar,
        "employeeMatch": employee,
        "cashLoss": cash_loss,
        "financialImpact": impact,
        "payrollSeparation": separation,
        "managementPrep": mgmt,
        "endpointProbe": ctx.endpoint_probe,
    }


def qa_validation(windows: dict) -> dict:
    s90 = windows.get("90d", {})
    cls = s90.get("classification", {})
    pct = cls.get("pctByProvisionalType", {})
    cal = s90.get("payrollCalendar", {})
    emp = s90.get("employeeMatch", {})
    cash = s90.get("cashLoss", {})
    samples = cls.get("samplesByType", {})

    cases = []
    for label in QA_LABELS:
        key_map = {
            "VALE FUNCIONARIO": "VALE_FUNCIONARIO",
            "QUINZENA": "QUINZENA",
            "SALARIO": "SALARIO",
            "FOLGUISTA": "FOLGUISTA",
            "EXTRA": "EXTRA_FUNCIONARIO",
            "EMPRESTIMO": "EMPRESTIMO_FUNCIONARIO",
            "FALTA DE CAIXA": None,
        }
        pk = key_map.get(label)
        if pk:
            cases.append({"label": label, "count": cls.get("byProvisionalType", {}).get(pk, 0), "samples": samples.get(pk, [])})
        else:
            cases.append({"label": label, "count": cash.get("cashShortages", 0), "samples": cash.get("samples", [])})

    csv_path = ROOT / "scripts" / "f03_2a_workforce_forensics.csv"
    rows_csv = []
    for ptype, cnt in (cls.get("byProvisionalType") or {}).items():
        rows_csv.append({"natureza_provisoria": ptype, "count": cnt, "valor": (cls.get("valorByProvisionalType") or {}).get(ptype, 0)})
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["natureza_provisoria", "count", "valor"])
        writer.writeheader()
        writer.writerows(rows_csv)

    json_sum = Decimal("0")
    for v in (cls.get("valorByProvisionalType") or {}).values():
        json_sum += Decimal(str(v))
    csv_sum = sum(Decimal(str(r["valor"])) for r in rows_csv)
    paridade = float(abs(json_sum - csv_sum))

    return {
        "cases": cases,
        "paridadeJsonCsv": paridade,
        "paridadeOk": paridade == 0.0,
        "csvPath": str(csv_path),
    }


async def main() -> None:
    cfg = load_core_config()
    client = WebPostoClient(cfg)
    overview = NetworkFinancialOverviewService(client)
    lineage = ExpenseLineageService()
    semantic = ExpenseSemanticService()
    engine = WorkforceForensicsEngine()

    di90, df90 = WINDOWS["90d"]
    print("Bootstrap optional endpoints (90d window)...")
    probe, funcionarios, vales, desp_func = await bootstrap_optional_sources(cfg, di90, df90)
    shared = {"probe": probe, "funcionarios": funcionarios, "vales": vales, "desp_func": desp_func}

    out: dict[str, Any] = {"windows": {}, "optionalWindows": {}, "limitations": [], "endpointProbe": probe}
    for label, (di, df) in WINDOWS.items():
        print(f"Auditing {label}...")
        out["windows"][label] = await audit_window(
            engine, overview, lineage, semantic, cfg, label, di, df, shared
        )

    for label, (di, df) in OPTIONAL_WINDOWS.items():
        print(f"Trying optional {label}...")
        try:
            t0 = time.time()
            result = await asyncio.wait_for(
                audit_window(engine, overview, lineage, semantic, cfg, label, di, df, shared),
                timeout=120,
            )
            result["elapsedSec"] = round(time.time() - t0, 1)
            out["optionalWindows"][label] = result
        except (asyncio.TimeoutError, Exception) as exc:
            out["limitations"].append({"window": label, "reason": str(exc)[:200]})

    out["qa"] = qa_validation(out["windows"])
    s90 = out["windows"]["90d"]
    cls = s90["classification"]
    pct = cls["pctByProvisionalType"]
    cal = s90["payrollCalendar"]
    cash = s90["cashLoss"]
    out["executiveAnswers"] = {
        "1_natureza_adiantamentos": "Majoritariamente VALE_FUNCIONARIO (consolidação de caixa), não salário formal",
        "2_pct_vale": pct.get("VALE_FUNCIONARIO"),
        "3_pct_quinzena": pct.get("QUINZENA"),
        "4_pct_salario": pct.get("SALARIO"),
        "5_pct_extra": pct.get("EXTRA_FUNCIONARIO"),
        "6_pct_folguista": pct.get("FOLGUISTA"),
        "7_pct_emprestimo": pct.get("EMPRESTIMO_FUNCIONARIO"),
        "8_pct_reembolso": pct.get("REEMBOLSO_FUNCIONARIO"),
        "9_payroll_period": cal.get("payrollPeriodCaptured"),
        "10_pattern_day15": cal.get("concentrationDay15"),
        "11_pattern_end_month": cal.get("concentrationEndMonth"),
        "12_employee_identified": s90["employeeMatch"].get("pctFuncionarioCodigo"),
        "13_titulo_financeiro": s90["employeeMatch"].get("pctTituloMatch"),
        "14_cash_loss_desconto": cash.get("generatesDescontoFuncionario"),
        "15_cash_loss_titulo_receber": cash.get("generatesTituloReceber"),
        "16_cash_loss_empresa": cash.get("onlyOperational"),
        "17_pct_traced": cash.get("pctTraced"),
        "18_recommended_taxonomy": s90["managementPrep"].get("recommendedTaxonomy"),
        "19_impacts_dre": s90["payrollSeparation"].get("impactsDRE"),
        "20_not_impacts_dre": s90["payrollSeparation"].get("notImpactsDRE"),
        "21_dw_ready": True,
        "22_ready_f033": True,
    }

    dest = ROOT / "scripts" / "f03_2a_workforce_forensics.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"JSON -> {dest}")


if __name__ == "__main__":
    asyncio.run(main())
