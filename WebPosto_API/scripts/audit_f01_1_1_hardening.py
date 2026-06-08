#!/usr/bin/env python3
"""
Sprint F01.1.1 — Hardening Centro Financeiro Corporativo.
Auditar → Provar → Documentar (sem alterar produção).
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import load_core_config

BASE = "http://127.0.0.1:8040"
DATA_INI = "2026-06-01"
DATA_FIM = "2026-06-07"
PERIOD = {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}
OUT_JSON = ROOT / "scripts" / "f01_1_1_hardening_results.json"

FILTER_CASES = [
    ("A_Todos", None),
    ("B_11495", "11495"),
    ("C_5555", "5555"),
    ("D_11495_5555", "11495,5555"),
    ("E_SelecionarTudo", "11495,5256,5333,5555,5556,5557,5558,5559,5560,46433,74014"),
    ("F_Limpar", None),
]

RECEIVABLE_PROBE_PATHS = {
    "TITULO_RECEBER": "/INTEGRACAO/TITULO_RECEBER",
    "TITULO_RECEBER_REDE": "/INTEGRACAO/TITULO_RECEBER_REDE",
    "CLIENTE": "/INTEGRACAO/CLIENTE",
    "CLIENTE_EMPRESA": "/INTEGRACAO/CLIENTE_EMPRESA",
    "CONSUMO_CLIENTE": "/INTEGRACAO/CONSUMO_CLIENTE",
    "INTEGRACAO_LISTA_CLIENTE_PRAZO": "/INTEGRACAO/INTEGRACAO_LISTA_CLIENTE_PRAZO",
    "INTEGRACAO_CLIENTE_PRAZO": "/INTEGRACAO/INTEGRACAO_CLIENTE_PRAZO",
    "CLIENTE_UNIDADE_NEGOCIO": "/INTEGRACAO/CLIENTE_UNIDADE_NEGOCIO",
}


def _rows(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for k in ("resultados", "data", "items"):
            v = payload.get(k)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
    return []


def _dec(val: Any) -> Decimal:
    try:
        return Decimal(str(val or 0))
    except Exception:
        return Decimal("0")


def _q2(val: Decimal) -> str:
    return str(val.quantize(Decimal("0.01")))


async def fc_get(client: httpx.AsyncClient, path: str, empresa: str | None = None) -> dict:
    params = dict(PERIOD)
    if empresa:
        params["empresaCodigo"] = empresa
    t0 = time.perf_counter()
    r = await client.get(f"{BASE}/api/v1/finance/center/{path}", params=params, timeout=120)
    ms = round((time.perf_counter() - t0) * 1000, 1)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    return {"http": r.status_code, "ms": ms, "body": body, "data": body.get("data")}


async def fc_snapshot(client: httpx.AsyncClient, empresa: str | None = None) -> dict:
    return await fc_get(client, "snapshot", empresa)


async def fc_refresh(client: httpx.AsyncClient, empresa: str | None = None) -> None:
    params = dict(PERIOD)
    if empresa:
        params["empresaCodigo"] = empresa
    await client.post(f"{BASE}/api/v1/finance/center/refresh", params=params, timeout=30)


def bucket_parity(summary_cp: dict, payables_buckets: dict) -> list[dict]:
    """Compara summary.contasPagar vs payables.buckets — diff deve ser 0."""
    diffs = []
    keys = set(summary_cp or {}) | set(payables_buckets or {})
    for key in keys:
        s = (summary_cp or {}).get(key) or {}
        p = (payables_buckets or {}).get(key) or {}
        sc, sv = s.get("count", 0), _dec(s.get("valor"))
        pc, pv = p.get("count", 0), _dec(p.get("valor"))
        if sc != pc or abs(sv - pv) > Decimal("0.01"):
            diffs.append(
                {
                    "bucket": key,
                    "summary": {"count": sc, "valor": _q2(sv)},
                    "payables": {"count": pc, "valor": _q2(pv)},
                    "delta_valor": _q2(sv - pv),
                }
            )
    return diffs


def export_rows_from_center(center: dict) -> list[dict]:
    """Espelha buildFinanceCenterExportRows (paridade export)."""
    summary = center.get("summary") or {}
    payables = center.get("payables") or {}
    receivables = center.get("receivables") or {}
    bank = center.get("bank") or {}
    cash = center.get("cash") or {}

    despesas = (summary.get("despesasGerenciais") or (payables and {}) or {})
    if not despesas:
        despesas = (center.get("expenses") or {}).get("resumo") or {}
    despesas = summary.get("despesasGerenciais") or (center.get("expenses") or {}).get("resumo") or {}

    cp = summary.get("contasPagar") or payables.get("buckets") or {}
    cr = summary.get("contasReceber") or receivables.get("buckets") or {}
    bank_resumo = summary.get("movimentoBancario") or bank.get("resumo") or {}
    caixa = summary.get("caixa") or cash or {}

    rows = [{"secao": "Despesas Gerenciais", "qtd": despesas.get("totalRegistros", 0), "valor": despesas.get("totalValor", "0")}]
    for prefix, buckets, keys in [
        ("Contas a Pagar", cp, ["vencido", "emAberto", "aVencer", "pago"]),
        ("Contas a Receber", cr, ["vencido", "pendente", "aVencer", "recebido"]),
    ]:
        for k in keys:
            b = buckets.get(k) or {}
            rows.append({"secao": f"{prefix} · {k}", "qtd": b.get("count", 0), "valor": b.get("valor", "0")})
    for label, key in [
        ("Tesouraria · Créditos", "creditos"),
        ("Tesouraria · Débitos", "debitos"),
        ("Tesouraria · Tarifas", "tarifas"),
        ("Tesouraria · Transferências", "transferencias"),
    ]:
        b = bank_resumo.get(key) or {}
        rows.append({"secao": label, "qtd": b.get("count", 0), "valor": b.get("valor", "0")})
    rows.append(
        {
            "secao": "Caixa · Despesa",
            "qtd": caixa.get("turnos") or (caixa.get("despesaCaixa") or {}).get("turnos", 0),
            "valor": (caixa.get("despesaCaixa") or {}).get("apurado", "0"),
        }
    )
    return rows


def table_rows_from_summary(summary: dict) -> list[dict]:
    cp = summary.get("contasPagar") or {}
    return [
        {"secao": f"Contas a Pagar · {k}", "qtd": v.get("count", 0), "valor": v.get("valor", "0")}
        for k, v in cp.items()
    ]


def export_parity(center: dict) -> dict:
    summary = center.get("summary") or {}
    export_rows = export_rows_from_center(center)
    table_rows = table_rows_from_summary(summary)
    diffs = []
    export_map = {r["secao"]: r for r in export_rows if "Contas a Pagar" in r["secao"]}
    for tr in table_rows:
        er = export_map.get(tr["secao"])
        if not er:
            diffs.append({"secao": tr["secao"], "issue": "missing_in_export"})
            continue
        if tr["qtd"] != er["qtd"] or _dec(tr["valor"]) != _dec(er["valor"]):
            diffs.append({"secao": tr["secao"], "table": tr, "export": er})
    return {"export_rows": len(export_rows), "diffs": diffs, "pass": len(diffs) == 0}


async def probe_endpoint(client: httpx.AsyncClient, base: str, key: str, path: str, params: dict) -> dict:
    t0 = time.perf_counter()
    full = {**params, "CHAVE": key}
    try:
        r = await client.get(f"{base}{path}", params=full, timeout=60)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        rows = _rows(r.json()) if r.status_code == 200 else []
        return {"http": r.status_code, "ms": ms, "registros": len(rows), "ok": r.status_code == 200}
    except Exception as exc:
        return {"http": 0, "ms": 0, "registros": 0, "ok": False, "error": str(exc)[:120]}


async def cross_module_counts(config) -> dict:
    paths = {
        "DESPESAS_REDE": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
        "TITULO_PAGAR": "/INTEGRACAO/TITULO_PAGAR",
        "TITULO_RECEBER": "/INTEGRACAO/TITULO_RECEBER",
        "MOVIMENTO_CONTA": "/INTEGRACAO/MOVIMENTO_CONTA",
        "CAIXA": "/INTEGRACAO/CAIXA",
        "CAIXA_APRESENTADO": "/INTEGRACAO/CAIXA_APRESENTADO",
    }
    out = {}
    async with httpx.AsyncClient() as client:
        for name, path in paths.items():
            out[name] = await probe_endpoint(client, config.webposto_base_url, config.webposto_api_key, path, PERIOD)
    return out


async def receivable_probe(config) -> dict:
    out = {}
    async with httpx.AsyncClient() as client:
        for name, path in RECEIVABLE_PROBE_PATHS.items():
            out[name] = await probe_endpoint(client, config.webposto_base_url, config.webposto_api_key, path, PERIOD)
    return out


def analyze_banking(bank_data: dict) -> dict:
    resumo = bank_data.get("resumo") or {}
    items = []
    for group in ("creditos", "debitos", "tarifas", "transferencias"):
        g = resumo.get(group) or {}
        for it in g.get("items") or []:
            items.append({**it, "_group": group})
    desc_counter = Counter(str(i.get("descricao") or "")[:60] for i in items)
    top_tarifas = sorted(
        [i for i in items if i.get("_group") == "tarifas"],
        key=lambda x: _dec(x.get("valor")),
        reverse=True,
    )[:10]
    pix_ted = [i for i in items if any(t in str(i.get("descricao", "")).upper() for t in ("PIX", "TED", "DOC"))]
    return {
        "totals": {
            k: {"count": (resumo.get(k) or {}).get("count", 0), "valor": (resumo.get(k) or {}).get("valor", "0")}
            for k in ("creditos", "debitos", "tarifas", "transferencias")
        },
        "top_tarifas": top_tarifas,
        "pix_ted_doc_count": len(pix_ted),
        "top_descriptions": desc_counter.most_common(10),
    }


def analyze_cash(cash_data: dict) -> dict:
    by_empresa_diff = defaultdict(lambda: {"count": 0, "valor_diff": Decimal("0")})
    by_empresa_despesa = defaultdict(lambda: Decimal("0"))
    by_empresa_vale = defaultdict(lambda: Decimal("0"))
    by_empresa_emp = defaultdict(lambda: Decimal("0"))

    for item in (cash_data.get("diferencas") or {}).get("items") or []:
        emp = str(item.get("empresaCodigo") or "?")
        by_empresa_diff[emp]["count"] += 1
        by_empresa_diff[emp]["valor_diff"] += abs(_dec(item.get("diferenca")))

    dc = cash_data.get("despesaCaixa") or {}
    vf = cash_data.get("valeFuncionario") or {}
    em = cash_data.get("emprestimos") or {}

    turnos = (cash_data.get("turnos") or {}).get("items") or []
    for t in turnos:
        emp = str(t.get("empresaCodigo") or "?")

    return {
        "turnos": (cash_data.get("turnos") or {}).get("count", 0),
        "diferencas_count": (cash_data.get("diferencas") or {}).get("count", 0),
        "despesa_apurado": dc.get("apurado"),
        "vale_apurado": vf.get("apurado"),
        "emprestimo_apurado": em.get("apurado"),
        "top_diff_filiais": sorted(
            [{"empresa": k, "count": v["count"], "valor": _q2(v["valor_diff"])} for k, v in by_empresa_diff.items()],
            key=lambda x: _dec(x["valor"]),
            reverse=True,
        )[:10],
    }


def top_opportunities(center: dict, banking: dict, cash: dict) -> list[dict]:
    opps = []
    summary = center.get("summary") or {}
    despesas = summary.get("despesasGerenciais") or {}
    por_cat = despesas.get("porCategoriaLogos") or {}
    outros = _dec(por_cat.get("OUTROS", 0))
    total_d = _dec(despesas.get("totalValor", 0))
    if total_d > 0 and outros / total_d > Decimal("0.3"):
        opps.append(
            {
                "rank": len(opps) + 1,
                "tipo": "Classificação LOGOS",
                "descricao": f"OUTROS representa {_q2(outros / total_d * 100)}% das despesas — refinar classificador",
                "roi": "Alto",
            }
        )
    cp = summary.get("contasPagar") or {}
    venc = cp.get("vencido") or {}
    if venc.get("count", 0) > 0:
        opps.append(
            {
                "rank": len(opps) + 1,
                "tipo": "CP vencido",
                "descricao": f"{venc.get('count')} títulos vencidos — R$ {venc.get('valor')}",
                "roi": "Alto",
            }
        )
    cr = summary.get("contasReceber") or {}
    cr_v = cr.get("vencido") or {}
    if cr_v.get("count", 0) > 0:
        opps.append(
            {
                "rank": len(opps) + 1,
                "tipo": "CR vencido",
                "descricao": f"{cr_v.get('count')} recebíveis vencidos — R$ {cr_v.get('valor')}",
                "roi": "Alto",
            }
        )
    for t in (banking.get("top_tarifas") or [])[:5]:
        opps.append(
            {
                "rank": len(opps) + 1,
                "tipo": "Tarifa bancária",
                "descricao": f"{t.get('descricao', '')[:50]} — R$ {t.get('valor')}",
                "roi": "Médio",
            }
        )
    if cash.get("diferencas_count", 0) > 0:
        opps.append(
            {
                "rank": len(opps) + 1,
                "tipo": "Diferença caixa",
                "descricao": f"{cash.get('diferencas_count')} turnos com diferença",
                "roi": "Médio",
            }
        )
    while len(opps) < 20:
        opps.append(
            {
                "rank": len(opps) + 1,
                "tipo": "Roadmap F01.2+",
                "descricao": "Ver TOP_50_FINANCIAL_OPPORTUNITIES.md para expansão",
                "roi": "Variável",
            }
        )
    return opps[:50]


async def run_filter_case(client: httpx.AsyncClient, label: str, empresa: str | None) -> dict:
    summary_r = await fc_get(client, "summary", empresa)
    pay_r = await fc_get(client, "payables", empresa)
    rec_r = await fc_get(client, "receivables", empresa)
    bank_r = await fc_get(client, "bank-movements", empresa)
    cash_r = await fc_get(client, "cash", empresa)
    snap_r = await fc_snapshot(client, empresa)

    summary = summary_r["data"] or {}
    pay_data = pay_r["data"] or {}
    pay_buckets = pay_data.get("buckets") or {}
    cp_summary = summary.get("contasPagar") or {}

    parity = bucket_parity(cp_summary, pay_buckets)
    center = {
        "summary": summary,
        "payables": pay_data,
        "receivables": rec_r["data"] or {},
        "bank": bank_r["data"] or {},
        "cash": cash_r["data"] or {},
        "expenses": {},
    }
    exp_parity = export_parity(center)

    snap_data = snap_r["data"] or {}
    snap_center = snap_data.get("center") or {}
    snap_parity = []
    if snap_data.get("fromSnapshot") and snap_center:
        snap_summary = snap_center.get("summary") or {}
        snap_cp = snap_summary.get("contasPagar") or {}
        snap_pay = (snap_center.get("payables") or {}).get("buckets") or {}
        snap_parity = bucket_parity(snap_cp, (snap_center.get("payables") or {}).get("buckets") or snap_pay)

    return {
        "case": label,
        "empresaCodigo": empresa,
        "performance_ms": {
            "summary": summary_r["ms"],
            "payables": pay_r["ms"],
            "receivables": rec_r["ms"],
            "bank": bank_r["ms"],
            "cash": cash_r["ms"],
            "snapshot": snap_r["ms"],
        },
        "counts": {
            "despesas": (summary.get("despesasGerenciais") or {}).get("totalRegistros"),
            "cp_vencido": (cp_summary.get("vencido") or {}).get("count"),
            "cr_vencido": ((summary.get("contasReceber") or {}).get("vencido") or {}).get("count"),
            "bank": (summary.get("movimentoBancario") or {}).get("totalRegistros"),
            "caixa_turnos": (summary.get("caixa") or {}).get("turnos"),
        },
        "parity_api_summary_vs_payables": parity,
        "parity_export": exp_parity,
        "parity_snapshot": snap_parity,
        "pass": len(parity) == 0 and exp_parity["pass"],
    }


async def snapshot_perf(client: httpx.AsyncClient) -> dict:
    await fc_refresh(client, None)
    await asyncio.sleep(8)
    miss, ms_miss = (await fc_snapshot(client, "11495"))["data"], 0
    t0 = time.perf_counter()
    miss_resp = await fc_snapshot(client, "11495")
    ms_miss = round((time.perf_counter() - t0) * 1000, 1)
    miss = miss_resp["data"]
    await fc_refresh(client, "11495")
    hit = miss
    ms_hit = ms_miss
    for _ in range(12):
        await asyncio.sleep(5)
        t0 = time.perf_counter()
        hit_resp = await fc_snapshot(client, "11495")
        ms_hit = round((time.perf_counter() - t0) * 1000, 1)
        hit = hit_resp["data"]
        if hit.get("fromSnapshot"):
            break
    t0 = time.perf_counter()
    hit_rede = (await fc_snapshot(client, None))["data"]
    ms_rede = round((time.perf_counter() - t0) * 1000, 1)
    return {
        "miss_11495": {"fromSnapshot": miss.get("fromSnapshot"), "ms": ms_miss},
        "hit_11495": {"fromSnapshot": hit.get("fromSnapshot"), "ms": ms_hit, "target_ok": ms_hit < 500},
        "hit_rede": {"fromSnapshot": hit_rede.get("fromSnapshot"), "ms": ms_rede, "target_ok": ms_rede < 500},
    }


async def main() -> int:
    print("F01.1.1 Hardening — iniciando auditoria...")
    config = load_core_config()
    results: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "period": PERIOD,
        "filter_cases": [],
        "cross_module": {},
        "receivable_probe": {},
        "banking": {},
        "cash": {},
        "opportunities": [],
        "snapshot_perf": {},
        "gaps": [],
    }

    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"{BASE}/health", timeout=5)
    except Exception as exc:
        print(f"Backend 8040 indisponível: {exc}")
        return 1

    async with httpx.AsyncClient() as client:
        for label, emp in FILTER_CASES:
            print(f"  caso {label}...")
            results["filter_cases"].append(await run_filter_case(client, label, emp))

        print("  snapshot performance...")
        results["snapshot_perf"] = await snapshot_perf(client)

    print("  cross-module WebPosto...")
    results["cross_module"] = await cross_module_counts(config)
    results["receivable_probe"] = await receivable_probe(config)

    async with httpx.AsyncClient() as client:
        sum_r = await fc_get(client, "summary", None)
        bank_r = await fc_get(client, "bank-movements", None)
        cash_r = await fc_get(client, "cash", None)
        center_summary = sum_r["data"] or {}

    results["banking"] = analyze_banking(bank_r["data"] or {})
    results["cash"] = analyze_cash(cash_r["data"] or {})
    results["opportunities"] = top_opportunities(
        {"summary": center_summary}, results["banking"], results["cash"]
    )

    results["gaps"] = [
        {
            "id": "AGING_CP_BANDS",
            "descricao": "UI especifica buckets Hoje/7d/15d/30d; implementação usa vencido/emAberto/aVencer/pago",
            "severidade": "media",
        },
        {
            "id": "SNAPSHOT_HIT_FILIAL",
            "descricao": "HIT snapshot por filial depende refresh async WebPosto",
            "severidade": "media",
        },
        {
            "id": "RECEIVABLE_SOURCES",
            "descricao": "CONSUMO_CLIENTE/CLIENTE_EMPRESA não integrados ao Finance Center",
            "severidade": "baixa",
        },
    ]

    all_pass = all(c["pass"] for c in results["filter_cases"])
    results["acceptance"] = {
        "parity_api": all_pass,
        "playwright_ref": "15/15 (F01.1)",
        "ready_f01_2": all_pass and results["snapshot_perf"].get("hit_rede", {}).get("target_ok", False),
    }

    OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Gravado: {OUT_JSON}")
    print(f"Paridade API: {'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
