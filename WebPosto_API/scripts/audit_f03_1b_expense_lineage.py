#!/usr/bin/env python3
"""F03.1-B — Expense Lineage Intelligence audit (read-only)."""
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
from src.services.expense_lineage_service import ExpenseLineageService, SOURCE_TAXONOMY, _norm_text
from src.services.expense_lineage_snapshot_service import ExpenseLineageSnapshotService
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService

WINDOWS = {
    "7d": ("2026-06-01", "2026-06-07"),
    "30d": ("2026-05-08", "2026-06-07"),
    "90d": ("2026-03-09", "2026-06-07"),
}

QA_CASE = {"empresaCodigo": 5555, "data": "2026-06-08", "termo": "BOBINA"}


def _load_empresa_names() -> dict[int, str]:
    names: dict[int, str] = {}
    for path in (ROOT / "snapshots" / "executive").glob("*_all.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for block in doc.get("filiais", []):
            code = block.get("empresaCodigo")
            label = block.get("nomeFantasia") or block.get("nome")
            if code and label:
                names[int(code)] = str(label)
    return names


def _bobina_study(rows: list[dict], despesas_rede: list[dict]) -> dict:
    screen_hits = [
        r for r in rows if "BOBINA" in _norm_text(r.get("descricao") or r.get("planoConta") or "")
    ]
    rede_hits = [
        r for r in despesas_rede if "BOBINA" in _norm_text(r.get("descricaoDocumento") or r.get("descricao") or "")
    ]
    empresas = sorted({r.get("empresaCodigo") for r in screen_hits + rede_hits})
    datas = sorted({str(r.get("data") or "")[:10] for r in screen_hits})
    return {
        "ocorrenciasTela": len(screen_hits),
        "ocorrenciasRede": len(rede_hits),
        "empresas": empresas,
        "datas": datas,
        "amostraTela": [
            {
                "empresaCodigo": r.get("empresaCodigo"),
                "data": r.get("data"),
                "valor": r.get("valor"),
                "origem": r.get("origem"),
                "origemReal": r.get("origemReal"),
                "fornecedor": r.get("fornecedor"),
                "planoConta": r.get("planoConta"),
                "centroCusto": r.get("centroCusto"),
                "documento": r.get("documento"),
                "lineagePath": r.get("lineagePath"),
            }
            for r in screen_hits[:10]
        ],
        "amostraRede": [
            {
                "empresaCodigo": r.get("empresaCodigo"),
                "data": str(r.get("data") or r.get("dataMovimento") or "")[:10],
                "valor": r.get("valor"),
                "descricao": r.get("descricaoDocumento") or r.get("descricao"),
                "planoConta": r.get("planoContaGerencialDescricao") or r.get("planoConta"),
                "centroCusto": r.get("centroCustoDescricao") or r.get("centroCusto"),
            }
            for r in rede_hits[:10]
        ],
    }


async def audit_window(
    overview: NetworkFinancialOverviewService,
    lineage: ExpenseLineageService,
    label: str,
    di: str,
    df: str,
    empresa_names: dict[int, str],
) -> dict:
    filters = FinancialOverviewFilters(data_inicial=di, data_final=df)
    t0 = time.time()
    payload = await lineage.build_lineage_payload(overview, filters)
    rows = payload.get("rows") or []
    summary = payload.get("summary") or {}
    ctx_sizes = payload.get("contextSizes") or {}

    untraced = [r for r in rows if not r.get("rastreabilidadeOk")]
    ctx = await lineage.build_context(overview, filters)
    bobina = _bobina_study(rows, ctx.despesas_rede)

    return {
        "window": label,
        "periodo": {"inicio": di, "fim": df},
        "elapsedSec": round(time.time() - t0, 1),
        "summary": summary,
        "contextSizes": ctx_sizes,
        "caseStudies": payload.get("caseStudies") or [],
        "sourceFieldMatrix": payload.get("sourceFieldMatrix") or {},
        "operationalFinancial": summary.get("operationalFinancial") or {},
        "untracedCount": len(untraced),
        "untracedSample": untraced[:5],
        "bobinaTermica": bobina,
        "sourceTaxonomy": SOURCE_TAXONOMY,
        "paridade": {
            "screenRecords": summary.get("totalRecords"),
            "tracedRecords": summary.get("tracedRecords"),
            "delta": summary.get("totalRecords", 0) - summary.get("tracedRecords", 0),
        },
    }


async def qa_bobina_case(overview: NetworkFinancialOverviewService, lineage: ExpenseLineageService) -> dict:
    filters = FinancialOverviewFilters(
        data_inicial=QA_CASE["data"],
        data_final=QA_CASE["data"],
        empresa_codigo=QA_CASE["empresaCodigo"],
    )
    payload = await lineage.build_lineage_payload(overview, filters)
    rows = payload.get("rows") or []
    bobina_rows = [
        r for r in rows if QA_CASE["termo"] in _norm_text(r.get("descricao") or r.get("planoConta") or "")
    ]
    api_rows, _ = await overview._load_screen_expenses(filters)
    paridade_valor = sum(Decimal(str(r.get("valor") or 0)) for r in rows) - sum(
        Decimal(str(r.get("valor") or 0)) for r in api_rows
    )
    return {
        "case": QA_CASE,
        "totalTela": len(rows),
        "bobinaRows": bobina_rows,
        "paridadeValor": float(paridade_valor),
        "paridadeOk": paridade_valor == 0,
        "lineagePaths": [r.get("lineagePath") for r in bobina_rows],
    }


async def main() -> None:
    cfg = load_core_config()
    client = WebPostoClient(cfg)
    overview = NetworkFinancialOverviewService(client)
    lineage = ExpenseLineageService()
    snapshot = ExpenseLineageSnapshotService(overview, lineage)
    empresa_names = _load_empresa_names()

    results: dict = {"windows": {}, "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S")}
    for label, (di, df) in WINDOWS.items():
        print(f"Auditing {label}...", flush=True)
        results["windows"][label] = await audit_window(overview, lineage, label, di, df, empresa_names)

    print("QA BOBINA case...", flush=True)
    results["qaBobina"] = await qa_bobina_case(overview, lineage)

    filters_90 = FinancialOverviewFilters(data_inicial=WINDOWS["90d"][0], data_final=WINDOWS["90d"][1])
    snap = await snapshot.collect(filters_90)
    results["snapshot"] = {
        "lastUpdated": snap.get("lastUpdated"),
        "coveragePct": snap.get("summary", {}).get("coveragePct"),
        "keys": [
            f"expense:{d}:{WINDOWS['90d'][0]}:{WINDOWS['90d'][1]}:all"
            for d in ("lineage", "sources", "categories", "operators", "pdvs")
        ],
    }

    s90 = results["windows"]["90d"]["summary"]
    opf = s90.get("operationalFinancial") or {}
    results["executiveAnswers"] = {
        "1_deOndeVem": "DESPESA→Origem Técnica→Origem Negócio→Documento→Fornecedor→Plano→Centro→PDV→Turno→Operador",
        "2_fontes": list(SOURCE_TAXONOMY.keys()),
        "3_pctFinanceiro": s90.get("pctFinanceiro"),
        "4_pctCaixa": s90.get("pctCaixa"),
        "5_pctPdv": s90.get("pctPdv"),
        "6_pctTesouraria": s90.get("pctTesouraria"),
        "7_categoriasDominantes": s90.get("byClassificacao"),
        "8_fornecedoresDominantes": s90.get("topSuppliers"),
        "9_topPdvs": s90.get("topPdvs"),
        "10_topOperators": s90.get("topOperators"),
        "11_bobinaLineage": results["qaBobina"].get("lineagePaths"),
        "12_coberturaFinanceira": s90.get("coverageFinanceiraPct"),
        "13_coberturaOperacional": s90.get("coverageOperacionalPct"),
        "14_pctMatchExato": opf.get("pct", {}).get("MATCH_EXATO"),
        "15_pctMatchParcial": opf.get("pct", {}).get("MATCH_PARCIAL"),
        "16_todaOperacionalGeraFinanceira": opf.get("allOperationalGenerateFinancial"),
        "17_pctGera": opf.get("pctWithFinancial"),
        "18_pctNaoGera": opf.get("pctWithoutFinancial"),
        "19_categoriasNuncaFinanceiro": s90.get("categoriesNeverFinancial"),
        "20_categoriasSempreFinanceiro": s90.get("categoriesAlwaysFinancial"),
        "21_avgLineageConfidence": s90.get("avgLineageConfidence"),
        "22_untraced": results["windows"]["90d"]["untracedCount"],
        "23_dwReady": "modelo_documentado",
        "24_uiReady": True,
    }

    out = ROOT / "scripts" / "f03_1b_expense_lineage.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"JSON -> {out}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
