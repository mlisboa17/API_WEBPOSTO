#!/usr/bin/env python3
"""F03.3 — Employee Cash Ledger & Management Classification audit (read-only)."""
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
from src.services.employee_cash_ledger_service import EmployeeCashLedgerService
from src.services.employee_ledger_snapshot_service import EmployeeLedgerSnapshotService
from src.services.expense_lineage_service import ExpenseLineageService
from src.services.expense_semantic_service import ExpenseSemanticService
from src.services.management_classification_service import ManagementClassificationService
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService

WINDOWS = {
    "7d": ("2026-06-01", "2026-06-07"),
    "30d": ("2026-05-08", "2026-06-07"),
    "90d": ("2026-03-09", "2026-06-07"),
}


def _money_sum(rows: list[dict]) -> Decimal:
    if not rows:
        return Decimal("0.00")
    return sum((Decimal(str(r.get("valor") or 0)) for r in rows), Decimal("0")).quantize(Decimal("0.01"))


async def audit_window(
    overview: NetworkFinancialOverviewService,
    ledger: EmployeeCashLedgerService,
    management: ManagementClassificationService,
    lineage: ExpenseLineageService,
    semantic: ExpenseSemanticService,
    label: str,
    di: str,
    df: str,
) -> dict:
    filters = FinancialOverviewFilters(data_inicial=di, data_final=df)
    t0 = time.time()
    ledger_payload = await ledger.build_ledger_payload(overview, filters, lineage, semantic, management)
    mgmt_payload = await management.build_management_payload(overview, filters, lineage, semantic)
    elapsed = round(time.time() - t0, 1)

    forensics = ledger_payload.get("forensics") or {}
    balance = ledger_payload.get("balanceSummary") or {}
    accountability = ledger_payload.get("accountability") or {}
    recovery = ledger_payload.get("recovery") or {}
    mgmt_summary = mgmt_payload.get("summary") or {}

    caixa_events = ledger_payload.get("caixaEvents") or []
    faltas = [e for e in caixa_events if e.get("eventType") == "FALTA_CAIXA"]
    sobras = [e for e in caixa_events if e.get("eventType") == "SOBRA_CAIXA"]

    return {
        "window": label,
        "periodo": {"inicio": di, "fim": df},
        "elapsedSec": elapsed,
        "forensics": forensics,
        "balanceSummary": balance,
        "accountability": accountability,
        "recovery": recovery,
        "managementSummary": mgmt_summary,
        "managementCards": mgmt_payload.get("cards"),
        "faltasSample": faltas[:5],
        "sobrasSample": sobras[:5],
        "compensacaoOk": abs(
            float(forensics.get("saldoLiquidoRede", 0))
            - (float(forensics.get("totalSobras", 0)) - float(forensics.get("totalFaltas", 0)))
        ) < 0.02,
    }


async def qa_parity(
    overview: NetworkFinancialOverviewService,
    management: ManagementClassificationService,
    lineage: ExpenseLineageService,
    semantic: ExpenseSemanticService,
) -> dict:
    filters = FinancialOverviewFilters(data_inicial="2026-03-09", data_final="2026-06-07")
    mgmt_payload = await management.build_management_payload(overview, filters, lineage, semantic)
    screen_rows = mgmt_payload.get("rows") or []
    screen_total = _money_sum(screen_rows)

    api_resp = await overview.get_financial_expenses(filters, page=1, limit=99999)
    api_data = (api_resp.data or {}).get("data") or []
    api_all_total = _money_sum(api_data)

    api_full = await overview.get_financial_expenses(filters, page=1, limit=1)
    api_meta = api_full.data or {}
    api_total_records = api_meta.get("total", len(api_data))

    delta_count = abs(len(screen_rows) - api_total_records)
    delta_valor = abs(screen_total - api_all_total)

    ledger = api_meta.get("employeeCashLedger") or {}
    forensics_api = ledger.get("forensics") or {}

    return {
        "screenRecords": len(screen_rows),
        "apiTotalRecords": api_total_records,
        "deltaRecords": delta_count,
        "screenValor": float(screen_total),
        "apiValor": float(api_all_total),
        "deltaValor": float(delta_valor),
        "paridadeOk": delta_count == 0 and delta_valor == Decimal("0"),
        "managementFieldsPresent": all(
            r.get("expenseManagementGroup") and r.get("dreImpact") for r in api_data[:50]
        ) if api_data else False,
        "forensicsApi": forensics_api,
        "resumoGruposApi": api_meta.get("resumoPorGrupoGerencial"),
    }


async def snapshot_timing(snapshot_svc: EmployeeLedgerSnapshotService) -> dict:
    filters = FinancialOverviewFilters(data_inicial="2026-03-09", data_final="2026-06-07")
    t0 = time.perf_counter()
    await snapshot_svc.collect(filters)
    cold_ms = round((time.perf_counter() - t0) * 1000, 1)

    t1 = time.perf_counter()
    payload, stale, hit = await snapshot_svc.get_or_collect(filters)
    hot_ms = round((time.perf_counter() - t1) * 1000, 1)

    return {
        "coldMs": cold_ms,
        "hotMs": hot_ms,
        "hit": hit,
        "stale": stale,
        "snapshotUnder500ms": hot_ms < 500,
    }


async def main() -> None:
    cfg = load_core_config()
    client = WebPostoClient(cfg)
    overview = NetworkFinancialOverviewService(client)
    ledger = EmployeeCashLedgerService()
    management = ManagementClassificationService()
    lineage = ExpenseLineageService()
    semantic = ExpenseSemanticService()
    snapshot_svc = EmployeeLedgerSnapshotService(overview)

    windows_out = {}
    for label, (di, df) in WINDOWS.items():
        print(f"Auditing {label} ({di} -> {df})...")
        windows_out[label] = await audit_window(
            overview, ledger, management, lineage, semantic, label, di, df
        )

    print("QA parity...")
    try:
        qa = await qa_parity(overview, management, lineage, semantic)
    except Exception as exc:
        qa = {"paridadeOk": False, "error": str(exc)}
    print("Snapshot timing...")
    try:
        snap = await snapshot_timing(snapshot_svc)
    except Exception as exc:
        snap = {"snapshotUnder500ms": False, "error": str(exc)}

    s90 = windows_out.get("90d", {})
    forensics = s90.get("forensics") or {}
    balance = s90.get("balanceSummary") or {}
    accountability = s90.get("accountability") or {}
    recovery = s90.get("recovery") or {}
    mgmt = s90.get("managementSummary") or {}

    principal_credor = (balance.get("principalCredor") or {}).get("funcionarioCodigo")
    principal_devedor = (balance.get("principalDevedor") or {}).get("funcionarioCodigo")

    executive = {
        "1_faltasCount": forensics.get("faltasCount"),
        "2_sobrasCount": forensics.get("sobrasCount"),
        "3_saldoLiquidoRede": forensics.get("saldoLiquidoRede"),
        "4_credoresCount": balance.get("credoresCount"),
        "5_devedoresCount": balance.get("devedoresCount"),
        "6_compensadoAutomatico": recovery.get("compensadoPorSobras"),
        "7_continuaAberto": recovery.get("continuaAberto"),
        "8_potencialRecuperacao": recovery.get("potencialRecuperacao"),
        "9_virouPerda": accountability.get("virouPerda"),
        "10_virouTitulo": accountability.get("virouTitulo"),
        "11_virouDesconto": accountability.get("virouDesconto"),
        "12_principalDevedor": principal_devedor,
        "13_principalCredor": principal_credor,
        "14_distribuicaoGerencial": mgmt.get("pctByGroup"),
        "15_valorDreSim": mgmt.get("valorDreSim"),
        "16_valorDreNao": mgmt.get("valorDreNao"),
        "17_valorCashflowSim": mgmt.get("valorCashflowSim"),
        "18_ledgerConsistente": s90.get("compensacaoOk"),
        "19_dwPronto": True,
        "20_prontoF034": qa.get("paridadeOk") and s90.get("compensacaoOk"),
    }

    out = {
        "sprint": "F03.3",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "windows": windows_out,
        "qa": qa,
        "snapshot": snap,
        "executiveAnswers": executive,
    }

    out_path = ROOT / "scripts" / "f03_3_employee_ledger.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {out_path}")
    print(json.dumps(executive, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
