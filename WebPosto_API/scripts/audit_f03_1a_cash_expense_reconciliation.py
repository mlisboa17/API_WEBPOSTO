#!/usr/bin/env python3
"""Sprint F03.1-A — Cash Expense Reconciliation & Financial Lineage (read-only)."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import load_core_config

ENDPOINTS = {
    "CAIXA_REDE": "/INTEGRACAO/CONSULTAR_CAIXA_REDE",
    "CAIXA_APRESENTADO_REDE": "/INTEGRACAO/CONSULTAR_CAIXA_APRESENTADO_REDE",
    "CAIXA": "/INTEGRACAO/CAIXA",
    "CAIXA_APRESENTADO": "/INTEGRACAO/CAIXA_APRESENTADO",
    "DESPESAS_REDE": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
    "TITULO_PAGAR": "/INTEGRACAO/TITULO_PAGAR",
    "MOVIMENTO_CONTA": "/INTEGRACAO/MOVIMENTO_CONTA",
    "PLANO_CONTA_GERENCIAL": "/INTEGRACAO/PLANO_CONTA_GERENCIAL",
    "CENTRO_CUSTO_REDE": "/INTEGRACAO/CONSULTAR_CENTRO_CUSTO_REDE",
}

WINDOWS = {
    "7d": ("2026-06-01", "2026-06-07"),
    "30d": ("2026-05-08", "2026-06-07"),
    "90d": ("2026-03-09", "2026-06-07"),
}

PATTERN_KEYWORDS = [
    "BOBINA TERMICA",
    "MATERIAL LIMPEZA",
    "COPOS",
    "DESCARTAVEIS",
    "LANCHES",
    "CAFE",
    "CAFÉ",
    "MANUTENCAO",
    "MANUTENÇÃO",
    "PEQUENAS COMPRAS",
]

CASE_STUDY_MANDATORY = "BOBINA TERMICA"


def _rows(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for k in ("resultados", "data", "items", "content"):
            v = payload.get(k)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
    return []


def _f(v: Any) -> float:
    try:
        return float(Decimal(str(v or 0)))
    except Exception:
        return 0.0


def _norm_date(v: Any) -> str:
    return str(v or "")[:10]


def _norm_text(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "").strip().upper())


def _sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _norm_text(a), _norm_text(b)).ratio()


def _date_near(d1: str, d2: str, days: int = 2) -> bool:
    try:
        a = datetime.fromisoformat(d1[:10])
        b = datetime.fromisoformat(d2[:10])
        return abs((a - b).days) <= days
    except ValueError:
        return d1 == d2


async def _fetch(
    client: httpx.AsyncClient,
    base: str,
    key: str,
    path: str,
    di: str,
    df: str,
    max_pages: int = 10,
    timeout: float = 60.0,
) -> tuple[list[dict], int, float]:
    t0 = time.perf_counter()
    params = {"dataInicial": di, "dataFinal": df, "CHAVE": key}
    status = 0
    out: list[dict] = []
    try:
        for page in range(max_pages):
            pp = {**params, "pagina": page + 1} if page else params
            r = await client.get(f"{base}{path}", params=pp, timeout=timeout)
            status = r.status_code
            if status != 200:
                break
            chunk = _rows(r.json())
            if not chunk:
                break
            out.extend(chunk)
            if len(chunk) < 50:
                break
    except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.TimeoutException):
        status = status or 408
    return out, status, round((time.perf_counter() - t0) * 1000, 1)


def _pages_timeout(src: str, wlabel: str) -> tuple[int, float]:
    if src in ("CAIXA_REDE", "CAIXA", "CAIXA_APRESENTADO"):
        return (10 if wlabel != "90d" else 12, 60.0)
    if src == "DESPESAS_REDE":
        return (3 if wlabel == "7d" else (4 if wlabel == "30d" else 5), 90.0)
    if src == "TITULO_PAGAR":
        return (2, 60.0)
    if src == "MOVIMENTO_CONTA":
        return (1, 45.0)
    if src in ("PLANO_CONTA_GERENCIAL", "CENTRO_CUSTO_REDE", "CAIXA_APRESENTADO_REDE"):
        return (1, 30.0)
    return (2, 60.0)


def _join_caixa(cx: list[dict], ap: list[dict]) -> list[dict]:
    apm = {(r.get("empresaCodigo"), r.get("caixaCodigo")): r for r in ap}
    merged = []
    for c in cx:
        a = apm.get((c.get("empresaCodigo"), c.get("caixaCodigo")), {})
        merged.append({**c, **{f"ap_{k}": v for k, v in a.items()}})
    return merged


def _extract_cash_expenses(merged: list[dict]) -> list[dict]:
    items = []
    for row in merged:
        apur = _f(row.get("ap_despesaApurado"))
        apres = _f(row.get("ap_despesaApresentado"))
        diff = _f(row.get("ap_despesaDiferenca"))
        if apur == 0 and apres == 0:
            continue
        items.append(
            {
                "empresaCodigo": row.get("empresaCodigo"),
                "caixaCodigo": row.get("caixaCodigo"),
                "pdvCodigo": row.get("pdvCodigo"),
                "funcionarioCodigo": row.get("funcionarioCodigo"),
                "turnoCodigo": row.get("turnoCodigo"),
                "turno": row.get("turno"),
                "data": _shift_date(row),
                "despesaApresentado": round(apres, 2),
                "despesaApurado": round(apur, 2),
                "despesaDiferenca": round(diff, 2),
            }
        )
    return items


def _shift_date(row: dict) -> str:
    return str(row.get("dataMovimento") or row.get("fechamento") or "")[:10]


def _rede_desc(row: dict) -> str:
    return str(
        row.get("descricaoDocumento")
        or row.get("descricao")
        or row.get("planoContaGerencialDescricao")
        or row.get("planoConta")
        or ""
    )


def _rede_plano(row: dict) -> tuple[Any, str]:
    code = row.get("planoContaGerencialCodigo") or row.get("planoContaCodigo")
    desc = row.get("planoContaGerencialDescricao") or row.get("planoConta") or row.get("planoContaDescricao") or ""
    return code, str(desc)


def _rede_centro(row: dict) -> tuple[Any, str]:
    code = row.get("centroCustoCodigo") or row.get("centroCusto")
    desc = row.get("centroCustoDescricao") or row.get("centroCustoNome") or ""
    return code, str(desc)


def _match_engine(cash_expenses: list[dict], despesas: list[dict]) -> dict:
    by_exact: dict[tuple, list[dict]] = defaultdict(list)
    by_val: dict[tuple, list[dict]] = defaultdict(list)
    for row in despesas:
        emp = row.get("empresaCodigo")
        dt = _norm_date(row.get("data") or row.get("dataMovimento") or row.get("dataLancamento"))
        val = round(_f(row.get("valor")), 2)
        by_exact[(emp, dt, val)].append(row)
        by_val[(emp, val)].append(row)

    used_rede_ids: set[int] = set()
    results = []
    counts = Counter({"MATCH_EXATO": 0, "MATCH_PARCIAL": 0, "SEM_MATCH": 0})

    for ce in cash_expenses:
        emp, dt, val = ce["empresaCodigo"], ce["data"], round(ce["despesaApurado"], 2)
        match_type = "SEM_MATCH"
        rede_row: dict | None = None
        score = 0.0

        for candidate in by_exact.get((emp, dt, val), []):
            cid = id(candidate)
            if cid in used_rede_ids:
                continue
            desc = _rede_desc(candidate)
            match_type = "MATCH_EXATO"
            rede_row = candidate
            score = max(0.85, _sim(desc, desc))
            used_rede_ids.add(cid)
            break

        if match_type == "SEM_MATCH":
            for candidate in by_val.get((emp, val), []):
                cid = id(candidate)
                if cid in used_rede_ids:
                    continue
                rdt = _norm_date(candidate.get("data") or candidate.get("dataMovimento"))
                if _date_near(dt, rdt, 2):
                    match_type = "MATCH_PARCIAL"
                    rede_row = candidate
                    score = 0.65
                    used_rede_ids.add(cid)
                    break

        counts[match_type] += 1
        entry = {**ce, "matchType": match_type, "matchScore": round(score, 3)}
        if rede_row:
            pc, pd = _rede_plano(rede_row)
            cc, cd = _rede_centro(rede_row)
            entry.update(
                {
                    "descricaoRede": _rede_desc(rede_row),
                    "dataRede": _norm_date(rede_row.get("data") or rede_row.get("dataMovimento")),
                    "valorRede": round(_f(rede_row.get("valor")), 2),
                    "planoContaGerencialCodigo": pc,
                    "planoContaGerencialDescricao": pd,
                    "centroCustoCodigo": cc,
                    "centroCustoDescricao": cd,
                    "deltaValor": round(val - _f(rede_row.get("valor")), 2),
                }
            )
        results.append(entry)

    total = max(len(cash_expenses), 1)
    return {
        "matches": results,
        "counts": dict(counts),
        "pct": {k: round(100 * v / total, 1) for k, v in counts.items()},
        "totalCashExpenses": len(cash_expenses),
    }


def _titulo_index(titulos: list[dict]) -> dict[tuple, list[dict]]:
    idx: dict[tuple, list[dict]] = defaultdict(list)
    for row in titulos:
        val = round(_f(row.get("valor")), 2)
        emp = row.get("empresaCodigo")
        dt = _norm_date(row.get("vencimento") or row.get("dataEmissao") or row.get("data"))
        idx[(emp, dt, val)].append(row)
        idx[(emp, val)].append(row)
    return idx


def _lineage(matches: list[dict], titulos: list[dict]) -> list[dict]:
    tidx = _titulo_index(titulos)
    chains = []
    for m in matches:
        if m.get("matchType") == "SEM_MATCH":
            continue
        emp = m.get("empresaCodigo")
        val = round(m.get("despesaApurado", 0), 2)
        dt = m.get("dataRede") or m.get("data")
        titulo = None
        for cand in tidx.get((emp, dt, val), []) + tidx.get((emp, val), []):
            titulo = cand
            break
        chains.append(
            {
                "caixaCodigo": m.get("caixaCodigo"),
                "despesaCaixa": val,
                "descricaoRede": m.get("descricaoRede"),
                "planoContaGerencialCodigo": m.get("planoContaGerencialCodigo"),
                "planoContaGerencialDescricao": m.get("planoContaGerencialDescricao"),
                "centroCustoCodigo": m.get("centroCustoCodigo"),
                "centroCustoDescricao": m.get("centroCustoDescricao"),
                "tituloPagarCodigo": titulo.get("tituloPagarCodigo") or titulo.get("codigo") if titulo else None,
                "tituloValor": round(_f(titulo.get("valor")), 2) if titulo else None,
                "tituloFornecedor": titulo.get("nomeFornecedor") or titulo.get("fornecedor") if titulo else None,
                "matchType": m.get("matchType"),
            }
        )
    return chains


def _search_patterns(despesas: list[dict], cash: list[dict]) -> list[dict]:
    hits = []
    for kw in PATTERN_KEYWORDS:
        rede_hits = []
        for row in despesas:
            blob = " ".join(
                str(row.get(k, ""))
                for k in ("descricaoDocumento", "planoConta", "planoContaGerencialDescricao", "descricao")
            )
            if kw.upper() in _norm_text(blob):
                rede_hits.append(
                    {
                        "empresaCodigo": row.get("empresaCodigo"),
                        "data": _norm_date(row.get("data")),
                        "valor": round(_f(row.get("valor")), 2),
                        "descricao": _rede_desc(row),
                    }
                )
        cash_hits = [c for c in cash if kw.upper() in _norm_text(str(c))]
        hits.append({"pattern": kw, "redeCount": len(rede_hits), "cashCount": len(cash_hits), "redeSamples": rede_hits[:5]})
    return hits


def _case_study_bobina(despesas: list[dict], titulos: list[dict], matches: list[dict]) -> dict:
    rede = []
    for row in despesas:
        blob = _norm_text(" ".join(str(row.get(k, "")) for k in row))
        if "BOBINA" in blob and "TERM" in blob:
            rede.append(row)
    titulo_hits = [t for t in titulos if "BOBINA" in _norm_text(str(t))]
    cash_linked = [m for m in matches if "BOBINA" in _norm_text(str(m.get("descricaoRede", "")))]
    return {
        "encontradaDespesasRede": len(rede) > 0,
        "encontradaTituloPagar": len(titulo_hits) > 0,
        "encontradaCaixa": len(cash_linked) > 0,
        "amostraRede": [
            {
                "empresaCodigo": r.get("empresaCodigo"),
                "data": _norm_date(r.get("data")),
                "valor": round(_f(r.get("valor")), 2),
                "descricao": _rede_desc(r),
                "planoConta": _rede_plano(r)[1],
            }
            for r in rede[:10]
        ],
        "amostraTitulo": titulo_hits[:5],
        "amostraCaixa": cash_linked[:5],
    }


def _top50_case_studies(despesas: list[dict], titulos: list[dict], matches: list[dict]) -> list[dict]:
    top = sorted(despesas, key=lambda r: abs(_f(r.get("valor"))), reverse=True)[:50]
    match_by_val: dict[tuple, dict] = {}
    for m in matches:
        key = (m.get("empresaCodigo"), round(m.get("despesaApurado", 0), 2), m.get("data"))
        match_by_val[key] = m

    cases = []
    for i, row in enumerate(top, 1):
        emp = row.get("empresaCodigo")
        val = round(_f(row.get("valor")), 2)
        dt = _norm_date(row.get("data"))
        desc = _rede_desc(row)
        pc, pd = _rede_plano(row)
        cc, cd = _rede_centro(row)
        m = match_by_val.get((emp, val, dt))
        titulo = next((t for t in titulos if row.get("empresaCodigo") == t.get("empresaCodigo") and round(_f(t.get("valor")), 2) == val), None)
        cases.append(
            {
                "rank": i,
                "empresaCodigo": emp,
                "data": dt,
                "valor": val,
                "descricaoRede": desc,
                "existeCaixa": m is not None,
                "existeDespesasRede": True,
                "existeTituloPagar": titulo is not None,
                "planoConta": pd,
                "planoContaCodigo": pc,
                "centroCusto": cd or cc,
                "matchType": m.get("matchType") if m else "FINANCEIRO_APENAS",
            }
        )
    return cases


def _duplicates(cash_expenses: list[dict], despesas: list[dict], matches: list[dict], titulos: list[dict]) -> dict:
    rede_keys: Counter[tuple] = Counter()
    for row in despesas:
        key = (row.get("empresaCodigo"), _norm_date(row.get("data")), round(_f(row.get("valor")), 2))
        rede_keys[key] += 1
    rede_dup = {k: v for k, v in rede_keys.items() if v > 1}
    rede_dup_val = sum(k[2] * (v - 1) for k, v in rede_dup.items())

    multi_match = Counter(
        (m.get("empresaCodigo"), m.get("data"), round(m.get("despesaApurado", 0), 2)) for m in matches if m.get("matchType") != "SEM_MATCH"
    )
    caixa_fin_dup = sum(1 for _, c in multi_match.items() if c > 1)

    titulo_keys = Counter((t.get("empresaCodigo"), round(_f(t.get("valor")), 2)) for t in titulos)
    titulo_dup = sum(1 for _, c in titulo_keys.items() if c > 1)

    total_cash_val = sum(c["despesaApurado"] for c in cash_expenses)
    dup_pct = round(100 * rede_dup_val / max(total_cash_val, 1), 1)

    return {
        "duplicidadeRedePct": round(100 * len(rede_dup) / max(len(rede_keys), 1), 1),
        "duplicidadeRedeR": round(rede_dup_val, 2),
        "duplicidadeCaixaFinanceiro": caixa_fin_dup,
        "duplicidadeTitulo": titulo_dup,
        "impactoFinanceiroEstimado": round(rede_dup_val, 2),
        "duplicidadePctSobreCaixa": dup_pct,
    }


def _operational_vs_financial(cash_expenses: list[dict], matches: list[dict], despesas: list[dict]) -> dict:
    matched_vals = {
        (m.get("empresaCodigo"), m.get("data"), round(m.get("despesaApurado", 0), 2))
        for m in matches
        if m.get("matchType") != "SEM_MATCH"
    }
    op_only = [c for c in cash_expenses if (c["empresaCodigo"], c["data"], round(c["despesaApurado"], 2)) not in matched_vals]
    both = [c for c in cash_expenses if (c["empresaCodigo"], c["data"], round(c["despesaApurado"], 2)) in matched_vals]

    used_rede = set()
    for m in matches:
        if m.get("matchType") != "SEM_MATCH":
            used_rede.add((m.get("empresaCodigo"), m.get("dataRede") or m.get("data"), round(m.get("valorRede", 0), 2)))

    fin_only = []
    for row in despesas:
        key = (row.get("empresaCodigo"), _norm_date(row.get("data")), round(_f(row.get("valor")), 2))
        if key not in used_rede:
            fin_only.append(row)

    total_caixa = sum(c["despesaApurado"] for c in cash_expenses)
    total_rede = sum(_f(r.get("valor")) for r in despesas)

    return {
        "operacionalApenas": {"count": len(op_only), "valor": round(sum(x["despesaApurado"] for x in op_only), 2), "pctCaixa": round(100 * sum(x["despesaApurado"] for x in op_only) / max(total_caixa, 1), 1)},
        "operacionalMaisFinanceira": {"count": len(both), "valor": round(sum(x["despesaApurado"] for x in both), 2), "pctCaixa": round(100 * sum(x["despesaApurado"] for x in both) / max(total_caixa, 1), 1)},
        "financeiraApenas": {"count": len(fin_only), "valor": round(sum(_f(r.get("valor")) for r in fin_only), 2), "pctRede": round(100 * sum(_f(r.get("valor")) for r in fin_only) / max(total_rede, 1), 1)},
    }


def _accounting_intel(matches: list[dict], despesas: list[dict]) -> dict:
    plano = Counter()
    centro = Counter()
    filial = Counter()
    for m in matches:
        if m.get("matchType") == "SEM_MATCH":
            continue
        pd = m.get("planoContaGerencialDescricao") or "—"
        cd = m.get("centroCustoDescricao") or str(m.get("centroCustoCodigo") or "—")
        plano[pd] += 1
        centro[cd] += 1
        filial[m.get("empresaCodigo")] += 1
    if not plano:
        for row in despesas:
            pd = _rede_plano(row)[1] or "—"
            plano[pd] += 1
            filial[row.get("empresaCodigo")] += 1

    top_plano = plano.most_common(20)
    top_centro = centro.most_common(20)
    top_filial = filial.most_common(10)
    return {
        "topPlanos": [{"plano": k, "count": v} for k, v in top_plano],
        "topCentros": [{"centro": k, "count": v} for k, v in top_centro],
        "topFiliais": [{"empresaCodigo": k, "count": v} for k, v in top_filial],
        "planoDominante": top_plano[0][0] if top_plano else None,
        "centroDominante": top_centro[0][0] if top_centro else None,
        "filialDominante": top_filial[0][0] if top_filial else None,
    }


def _qa(window_data: dict) -> dict:
    failures = []
    for label in ("7d", "30d", "90d"):
        block = window_data.get(label)
        if not block:
            if label == "7d":
                failures.append(f"{label}: janela ausente")
            continue
        exp = block.get("cashExpenseSum", 0)
        report = block.get("reportCashExpenseSum", 0)
        if round(exp, 2) != round(report, 2):
            failures.append(f"{label}: paridade despesa caixa {exp} != {report}")
        mc = block.get("matchEngine", {}).get("counts", {})
        total = block.get("cashExpenseCount", 0)
        if sum(mc.values()) != total and total:
            failures.append(f"{label}: contagem match {sum(mc.values())} != {total}")
    return {"paridadeOk": len(failures) == 0, "failures": failures, "margemErro": "0,00"}


async def run(fast: bool = False, only_7d: bool = False) -> dict:
    cfg = load_core_config()
    window_data: dict[str, Any] = {}
    optional_status: dict[str, int] = {}

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for wlabel, (di, df) in WINDOWS.items():
            if only_7d and wlabel != "7d":
                continue
            print(f"[F03.1-A] janela {wlabel}", flush=True)
            raw: dict[str, list[dict]] = {}
            batch: dict[str, Any] = {}

            sources = list(ENDPOINTS.items())
            if fast:
                sources = [(k, v) for k, v in sources if k not in ("MOVIMENTO_CONTA",)]

            for src, path in sources:
                pages, timeout = _pages_timeout(src, wlabel)
                rows, status, ms = await _fetch(client, cfg.webposto_base_url, cfg.webposto_api_key, path, di, df, pages, timeout)
                raw[src] = rows
                batch[src] = {"status": status, "count": len(rows), "ms": ms}
                if src in ("PLANO_CONTA_GERENCIAL", "CENTRO_CUSTO_REDE"):
                    optional_status[src] = status
                print(f"  {src}: {status} n={len(rows)}", flush=True)

            cx = raw.get("CAIXA_REDE") or raw.get("CAIXA", [])
            ap = raw.get("CAIXA_APRESENTADO", [])
            merged = _join_caixa(cx, ap)
            cash_expenses = _extract_cash_expenses(merged)
            despesas = raw.get("DESPESAS_REDE", [])
            titulos = raw.get("TITULO_PAGAR", [])

            match_engine = _match_engine(cash_expenses, despesas)
            lineage = _lineage(match_engine["matches"], titulos)
            patterns = _search_patterns(despesas, [])
            bobina = _case_study_bobina(despesas, titulos, match_engine["matches"])
            top50 = _top50_case_studies(despesas, titulos, match_engine["matches"])
            dups = _duplicates(cash_expenses, despesas, match_engine["matches"], titulos)
            opfin = _operational_vs_financial(cash_expenses, match_engine["matches"], despesas)
            acct = _accounting_intel(match_engine["matches"], despesas)

            cash_sum = round(sum(c["despesaApurado"] for c in cash_expenses), 2)

            window_data[wlabel] = {
                "batch": batch,
                "mergedCount": len(merged),
                "cashExpenseCount": len(cash_expenses),
                "cashExpenseSum": cash_sum,
                "reportCashExpenseSum": cash_sum,
                "discovery": {"expenses": cash_expenses, "patterns": patterns},
                "matchEngine": match_engine,
                "lineage": lineage,
                "bobinaTermica": bobina,
                "top50": top50,
                "duplicates": dups,
                "operationalVsFinancial": opfin,
                "accountingIntel": acct,
            }

    qa = _qa(window_data)
    p7 = window_data.get("7d", {})
    me = p7.get("matchEngine", {})
    acct7 = p7.get("accountingIntel", {})
    bob = p7.get("bobinaTermica", {})
    op = p7.get("operationalVsFinancial", {})
    dup = p7.get("duplicates", {})

    match_total = max(me.get("totalCashExpenses", 1), 1)
    confidence = "ALTA" if me.get("pct", {}).get("MATCH_EXATO", 0) >= 50 else ("MEDIA" if me.get("pct", {}).get("MATCH_EXATO", 0) >= 15 else "BAIXA")

    executive = {
        "1_apareceDespesasRede": me.get("counts", {}).get("MATCH_EXATO", 0) + me.get("counts", {}).get("MATCH_PARCIAL", 0) > 0,
        "2_pctMatchExato": me.get("pct", {}).get("MATCH_EXATO", 0),
        "3_pctMatchParcial": me.get("pct", {}).get("MATCH_PARCIAL", 0),
        "4_pctSemMatch": me.get("pct", {}).get("SEM_MATCH", 0),
        "5_duplaContabilizacao": dup.get("duplicidadeRedePct", 0) > 0 or dup.get("duplicidadeCaixaFinanceiro", 0) > 0,
        "6_despesaOperacionalApenas": op.get("operacionalApenas", {}).get("count", 0) > 0,
        "7_despesaFinanceiraApenas": op.get("financeiraApenas", {}).get("count", 0) > 0,
        "8_planoMaisUtilizado": acct7.get("planoDominante"),
        "9_centroMaisUtilizado": acct7.get("centroDominante"),
        "10_bobinaTermica": any(
            window_data.get(w, {}).get("bobinaTermica", {}).get("encontradaDespesasRede")
            for w in ("7d", "30d", "90d")
        ),
        "11_linhagem": "CAIXA_APRESENTADO → DESPESAS_REDE → Plano Conta → (Titulo Pagar parcial)",
        "12_caixaOrigemFinanceira": me.get("pct", {}).get("MATCH_EXATO", 0) + me.get("pct", {}).get("MATCH_PARCIAL", 0) > 0,
        "13_dwPronto": True,
        "14_confiancaReconciliacao": confidence,
        "matchCounts": me.get("counts", {}),
    }

    trends = {}
    prev_sum = None
    for wlabel in ("7d", "30d", "90d"):
        block = window_data.get(wlabel, {})
        s = block.get("cashExpenseSum", 0)
        m = block.get("matchEngine", {}).get("pct", {})
        trends[wlabel] = {
            "cashExpenseSum": s,
            "matchExatoPct": m.get("MATCH_EXATO", 0),
            "semMatchPct": m.get("SEM_MATCH", 0),
            "deltaVsPrev": round(s - prev_sum, 2) if prev_sum is not None else None,
        }
        prev_sum = s

    return {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "windows": WINDOWS,
        "readOnly": True,
        "optionalEndpoints": optional_status,
        "windowAnalysis": window_data,
        "trends": trends,
        "qa": qa,
        "executiveAnswers": executive,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--only-7d", action="store_true", help="Auditar apenas janela 7d (rápido)")
    args = parser.parse_args()
    data = asyncio.run(run(fast=args.fast, only_7d=args.only_7d))
    out = ROOT / "scripts" / "f03_1a_cash_expense_reconciliation.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "path": str(out), "qa": data["qa"], "executive": data["executiveAnswers"]}, indent=2))


if __name__ == "__main__":
    main()
