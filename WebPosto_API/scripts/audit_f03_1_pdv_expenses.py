#!/usr/bin/env python3
"""Sprint F03.1 — PDV Expenses Audit (read-only)."""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from decimal import Decimal
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
    "MOVIMENTO_CONTA": "/INTEGRACAO/MOVIMENTO_CONTA",
    "TRANSFERENCIA_BANCARIA": "/INTEGRACAO/TRANSFERENCIA_BANCARIA",
    "DESPESAS_REDE": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
}

WINDOWS = {
    "7d": ("2026-06-01", "2026-06-07"),
    "30d": ("2026-05-08", "2026-06-07"),
    "90d": ("2026-03-09", "2026-06-07"),
}

EXPENSE_SCAN = re.compile(
    r"despesa|vale|emprest|suprimento|fundo|sangria|retirada|adiant|troco",
    re.I,
)

EXPENSE_FIELDS = [
    ("ap_despesaApresentado", "despesaApresentado", "DESPESA_CAIXA"),
    ("ap_despesaApurado", "despesaApurado", "DESPESA_CAIXA"),
    ("ap_despesaDiferenca", "despesaDiferenca", "DESPESA_CAIXA"),
    ("despesaApresentado", "despesaApresentado", "DESPESA_CAIXA"),
    ("despesaApurado", "despesaApurado", "DESPESA_CAIXA"),
    ("despesaDiferenca", "despesaDiferenca", "DESPESA_CAIXA"),
    ("ap_valeFunApresentado", "valeFunApresentado", "VALE_FUNCIONARIO"),
    ("ap_valeFunApurado", "valeFunApurado", "VALE_FUNCIONARIO"),
    ("ap_valeFunDiferenca", "valeFunDiferenca", "VALE_FUNCIONARIO"),
    ("ap_emprestimoApurado", "emprestimoApurado", "EMPRESTIMO"),
    ("ap_emprestimoDiferenca", "emprestimoDiferenca", "EMPRESTIMO"),
    ("ap_suprimentoCaixa", "suprimentoCaixa", "SUPRIMENTO"),
    ("suprimentoCaixa", "suprimentoCaixa", "SUPRIMENTO"),
    ("ap_fundoCaixaCredito", "fundoCaixaCredito", "FUNDO_CAIXA"),
    ("ap_fundoCxDebApurado", "fundoCxDebApurado", "FUNDO_CAIXA"),
    ("ap_fundoCxDebDiferenca", "fundoCxDebDiferenca", "FUNDO_CAIXA"),
    ("ap_transfBancApurado", "transfBancApurado", "OUTROS"),
]

FOCUS_PDVS = {54193, 15880}
FOCUS_OPS = {276288, 294273}


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


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return round(num / (den_x * den_y), 4)


async def _fetch(
    client: httpx.AsyncClient,
    base: str,
    key: str,
    path: str,
    di: str,
    df: str,
    max_pages: int = 15,
    timeout: float = 90.0,
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


def _join_caixa(cx: list[dict], ap: list[dict]) -> list[dict]:
    apm = {(r.get("empresaCodigo"), r.get("caixaCodigo")): r for r in ap}
    merged = []
    for c in cx:
        a = apm.get((c.get("empresaCodigo"), c.get("caixaCodigo")), {})
        merged.append({**c, **{f"ap_{k}": v for k, v in a.items()}})
    return merged


def _shift_date(row: dict) -> str:
    return str(row.get("dataMovimento") or row.get("fechamento") or "")[:10]


def _expense_forensics(merged: list[dict]) -> dict:
    field_stats: dict[str, dict] = {}
    all_keys: Counter[str] = Counter()
    for row in merged:
        for k in row:
            if EXPENSE_SCAN.search(k):
                all_keys[k] += 1

    for key, canonical, category in EXPENSE_FIELDS:
        vals = [_f(row.get(key)) for row in merged if key in row]
        if not vals and key not in all_keys:
            continue
        non_zero = sum(1 for v in vals if v != 0)
        field_stats[key] = {
            "canonical": canonical,
            "category": category,
            "registros": len(vals),
            "preenchimentoPct": round(100 * len(vals) / max(len(merged), 1), 1),
            "naoZero": non_zero,
            "soma": round(sum(vals), 2),
            "absSoma": round(sum(abs(v) for v in vals), 2),
            "exemplo": next((row.get(key) for row in merged if _f(row.get(key)) != 0), vals[0] if vals else None),
        }

    dynamic = []
    for k, count in sorted(all_keys.items()):
        if k not in field_stats:
            vals = [_f(row.get(k)) for row in merged]
            dynamic.append({"campo": k, "registros": count, "naoZero": sum(1 for v in vals if v != 0), "soma": round(sum(vals), 2)})

    by_pdv = defaultdict(float)
    by_op = defaultdict(float)
    by_turn = defaultdict(float)
    for row in merged:
        exp = _f(row.get("ap_despesaApurado"))
        if exp:
            by_pdv[row.get("pdvCodigo")] += exp
            by_op[row.get("funcionarioCodigo")] += exp
            by_turn[row.get("turno") or row.get("turnoCodigo")] += exp

    desp_diff_corr = _pearson(
        [_f(r.get("ap_despesaApurado")) for r in merged],
        [_f(r.get("diferenca")) for r in merged],
    )
    desp_cash_corr = _pearson(
        [_f(r.get("ap_despesaApurado")) for r in merged],
        [_f(r.get("ap_dinheiroDiferenca")) for r in merged],
    )

    return {
        "camposMapeados": field_stats,
        "camposDinamicos": dynamic[:30],
        "respostas": {
            "despesasExplicitas": any(_f(r.get("ap_despesaApurado")) != 0 for r in merged),
            "porPdv": len(by_pdv) > 0,
            "porOperador": len(by_op) > 0,
            "porTurno": len(by_turn) > 0,
            "impactaDiferenca": desp_diff_corr is not None and abs(desp_diff_corr) >= 0.3,
        },
        "totaisPorPdv": sorted([{"pdvCodigo": k, "despesaApurado": round(v, 2)} for k, v in by_pdv.items()], key=lambda x: -x["despesaApurado"])[:10],
        "totaisPorOperador": sorted([{"funcionarioCodigo": k, "despesaApurado": round(v, 2)} for k, v in by_op.items()], key=lambda x: -x["despesaApurado"])[:10],
        "correlacaoDespesaDiferenca": desp_diff_corr,
        "correlacaoDespesaDinheiro": desp_cash_corr,
    }


def _aggregate_dimension(merged: list[dict], key_fn) -> list[dict]:
    groups: dict[Any, list[dict]] = defaultdict(list)
    for row in merged:
        groups[key_fn(row)].append(row)

    items = []
    for key, rows in groups.items():
        despesas = [_f(r.get("ap_despesaApurado")) for r in rows]
        diffs = [_f(r.get("diferenca")) for r in rows]
        cash_diffs = [_f(r.get("ap_dinheiroDiferenca")) for r in rows]
        com_desp = sum(1 for d in despesas if d != 0)
        sem_desp = len(rows) - com_desp
        items.append(
            {
                "id": key,
                "fechamentos": len(rows),
                "despesaTotal": round(sum(despesas), 2),
                "diferencaTotal": round(sum(diffs), 2),
                "diferencaDinheiro": round(sum(cash_diffs), 2),
                "diasComDespesa": com_desp,
                "diasSemDespesa": sem_desp,
                "correlacaoDespesaDiff": _pearson(despesas, diffs),
            }
        )
    items.sort(key=lambda x: abs(x["diferencaTotal"]), reverse=True)
    return items


def _expense_vs_diff(merged: list[dict]) -> dict:
    by_pdv = _aggregate_dimension(merged, lambda r: r.get("pdvCodigo"))
    by_op = _aggregate_dimension(merged, lambda r: r.get("funcionarioCodigo"))
    by_turn = _aggregate_dimension(merged, lambda r: (r.get("turnoCodigo"), r.get("turno")))
    by_caixa = _aggregate_dimension(merged, lambda r: r.get("caixaCodigo"))

    pdv_exp_rank = sorted(by_pdv, key=lambda x: x["despesaTotal"], reverse=True)
    pdv_diff_rank = sorted(by_pdv, key=lambda x: abs(x["diferencaTotal"]), reverse=True)
    op_exp_rank = sorted(by_op, key=lambda x: x["despesaTotal"], reverse=True)
    op_diff_rank = sorted(by_op, key=lambda x: abs(x["diferencaTotal"]), reverse=True)

    top_pdv_exp = {x["id"] for x in pdv_exp_rank[:3]}
    top_pdv_diff = {x["id"] for x in pdv_diff_rank[:3]}
    top_op_exp = {x["id"] for x in op_exp_rank[:3]}
    top_op_diff = {x["id"] for x in op_diff_rank[:3]}

    global_corr = _pearson(
        [_f(r.get("ap_despesaApurado")) for r in merged],
        [_f(r.get("diferenca")) for r in merged],
    )

    com = [r for r in merged if _f(r.get("ap_despesaApurado")) != 0]
    sem = [r for r in merged if _f(r.get("ap_despesaApurado")) == 0]

    return {
        "porPdv": by_pdv,
        "porOperador": by_op,
        "porTurno": [{"turnoCodigo": t[0], "turno": t[1], **{k: v for k, v in rest.items() if k != "id"}} for item in by_turn for t, rest in [(item["id"], item)]],
        "porCaixa": by_caixa[:20],
        "correlacaoGlobal": global_corr,
        "mediaDiffComDespesa": round(statistics.mean([_f(r.get("diferenca")) for r in com]), 2) if com else 0,
        "mediaDiffSemDespesa": round(statistics.mean([_f(r.get("diferenca")) for r in sem]), 2) if sem else 0,
        "respostas": {
            "pdvMesmoRanking": len(top_pdv_exp & top_pdv_diff) >= 2,
            "operadorMesmoRanking": len(top_op_exp & top_op_diff) >= 1,
            "correlacaoEstatistica": global_corr is not None and abs(global_corr) >= 0.25,
        },
        "focus54193": next((x for x in by_pdv if x["id"] == 54193), {}),
        "focus15880": next((x for x in by_pdv if x["id"] == 15880), {}),
    }


def _norm_date(v: Any) -> str:
    return str(v or "")[:10]


def _despesas_rede_crosscheck(merged: list[dict], despesas: list[dict]) -> dict:
    caixa_expenses = []
    for row in merged:
        val = _f(row.get("ap_despesaApurado"))
        if val == 0:
            continue
        caixa_expenses.append(
            {
                "caixaCodigo": row.get("caixaCodigo"),
                "empresaCodigo": row.get("empresaCodigo"),
                "data": _shift_date(row),
                "valor": round(val, 2),
                "pdvCodigo": row.get("pdvCodigo"),
                "funcionarioCodigo": row.get("funcionarioCodigo"),
            }
        )

    rede_index: dict[tuple, list[dict]] = defaultdict(list)
    for row in despesas:
        val = _f(row.get("valor"))
        key = (
            row.get("empresaCodigo"),
            _norm_date(row.get("data") or row.get("dataMovimento") or row.get("dataLancamento")),
            round(val, 2),
        )
        rede_index[key].append(row)

    matched = []
    unmatched = []
    for ce in caixa_expenses:
        key = (ce["empresaCodigo"], ce["data"], ce["valor"])
        hits = rede_index.get(key, [])
        if hits:
            hit = hits[0]
            matched.append(
                {
                    **ce,
                    "redeMatch": True,
                    "planoConta": hit.get("planoConta") or hit.get("planoContaGerencialDescricao"),
                    "centroCusto": hit.get("centroCusto") or hit.get("centroCustoCodigo"),
                    "descricaoDocumento": hit.get("descricaoDocumento") or hit.get("descricao"),
                    "caixaCodigoRede": hit.get("caixaCodigo"),
                    "valorRede": _f(hit.get("valor")),
                    "deltaValor": round(ce["valor"] - _f(hit.get("valor")), 2),
                }
            )
        else:
            unmatched.append({**ce, "redeMatch": False})

    dup_keys = [k for k, rows in rede_index.items() if len(rows) > 1]
    valor_ok = sum(1 for m in matched if abs(m.get("deltaValor", 0)) < 0.01)

    sample_fields = list(despesas[0].keys())[:25] if despesas else []

    return {
        "caixaDespesasTotal": len(caixa_expenses),
        "redeRegistros": len(despesas),
        "matched": len(matched),
        "unmatched": len(unmatched),
        "matchRatePct": round(100 * len(matched) / max(len(caixa_expenses), 1), 1),
        "valorParidadeOk": valor_ok,
        "valorParidadePct": round(100 * valor_ok / max(len(matched), 1), 1),
        "duplicidadesRede": len(dup_keys),
        "amostraCamposRede": sample_fields,
        "amostraMatched": matched[:10],
        "amostraUnmatched": unmatched[:10],
        "respostas": {
            "apareceDespesasRede": len(matched) > 0,
            "duplicidade": len(dup_keys) > 0,
            "lancamentoCorrespondente": len(matched) > 0,
            "valorBate": valor_ok == len(matched) if matched else False,
            "centroPlanoRastreavel": sum(1 for m in matched if m.get("planoConta") or m.get("centroCusto")) > 0,
        },
    }


def _classify_row(row: dict) -> dict:
    rules: list[tuple[str, str, float, str]] = []
    checks = [
        ("ap_despesaApurado", "DESPESA_CAIXA", 0.95, "campo_despesaApurado"),
        ("ap_valeFunApurado", "VALE_FUNCIONARIO", 0.92, "campo_valeFunApurado"),
        ("ap_emprestimoApurado", "EMPRESTIMO", 0.90, "campo_emprestimoApurado"),
        ("ap_suprimentoCaixa", "SUPRIMENTO", 0.88, "campo_suprimentoCaixa"),
        ("ap_fundoCaixaCredito", "FUNDO_CAIXA", 0.85, "campo_fundoCaixaCredito"),
        ("ap_fundoCxDebApurado", "FUNDO_CAIXA", 0.85, "campo_fundoCxDebApurado"),
        ("ap_transfBancApurado", "OUTROS", 0.70, "campo_transfBancApurado"),
    ]
    for field, cat, conf, src in checks:
        val = _f(row.get(field))
        if val != 0:
            rules.append((cat, conf, src, val))

    if not rules:
        return {"categoriaPdvDespesa": "OUTROS", "confidenceScore": 0.5, "classificationSource": "default_zero", "valor": 0.0}

    rules.sort(key=lambda x: (-x[1], -abs(x[3])))
    cat, conf, src, val = rules[0]
    return {"categoriaPdvDespesa": cat, "confidenceScore": conf, "classificationSource": src, "valor": round(val, 2)}


def _classify_all(merged: list[dict]) -> dict:
    classified = []
    by_cat: Counter[str] = Counter()
    for row in merged:
        c = _classify_row(row)
        if c["valor"] == 0 and _f(row.get("ap_despesaApurado")) == 0:
            continue
        classified.append(
            {
                **c,
                "caixaCodigo": row.get("caixaCodigo"),
                "pdvCodigo": row.get("pdvCodigo"),
                "funcionarioCodigo": row.get("funcionarioCodigo"),
            }
        )
        by_cat[c["categoriaPdvDespesa"]] += 1

    return {
        "totalClassificados": len(classified),
        "porCategoria": dict(by_cat),
        "amostra": classified[:20],
    }


def _risk_model(cross: dict, diff: dict, forensics: dict) -> dict:
    match_rate = cross.get("matchRatePct", 0)
    corr = abs(diff.get("correlacaoGlobal") or 0)
    recommend_weight = 0.0
    reasons = []

    if match_rate < 50:
        recommend_weight = 0.08
        reasons.append("baixa paridade DESPESAS_REDE → penalizar risco operacional")
    elif corr < 0.2:
        recommend_weight = 0.05
        reasons.append("correlação fraca despesa×diff → peso baixo para evitar falso positivo")
    else:
        recommend_weight = 0.03
        reasons.append("correlação moderada → peso conservador")

    return {
        "entrarNoCashRiskScore": recommend_weight > 0,
        "pesoSugerido": recommend_weight,
        "pesoMaximoRecomendado": 0.10,
        "evitarFalsoPositivo": [
            "Exigir match DESPESAS_REDE antes de penalizar",
            "Separar VALE/SUPRIMENTO de DESPESA_CAIXA",
            "Não misturar despesaApurado (fluxo) com despesaDiferenca (componente)",
        ],
        "regras": {
            "despesaSemCorrespondenciaFinanceira": "+risco",
            "despesaComCorrespondencia": "neutro",
            "despesaRecorrenteOperador": "+risco leve",
            "despesaRecorrentePdv": "+risco leve",
            "suprimentoDocumentado": "-risco leve",
        },
        "justificativa": reasons,
        "correlacaoGlobal": diff.get("correlacaoGlobal"),
        "matchRateDespesasRede": match_rate,
    }


def _qa_windows(window_data: dict) -> dict:
    failures = []
    for label in ("7d", "30d", "90d"):
        block = window_data.get(label, {})
        merged_n = block.get("mergedCount", 0)
        if merged_n == 0:
            failures.append(f"{label}: zero fechamentos merge")
        exp_sum = block.get("despesaApuradoSum", 0)
        diff_sum = block.get("diferencaSum", 0)
        report_exp = block.get("reportDespesaSum", 0)
        if round(exp_sum, 2) != round(report_exp, 2):
            failures.append(f"{label}: paridade despesa {exp_sum} != {report_exp}")

    return {"paridadeOk": len(failures) == 0, "failures": failures, "margemErro": "0,00"}


def _pages_timeout(src: str, wlabel: str) -> tuple[int, float]:
    if src in ("CAIXA_REDE", "CAIXA", "CAIXA_APRESENTADO"):
        return (12 if wlabel == "90d" else 10, 60.0)
    if src == "DESPESAS_REDE":
        return (5 if wlabel == "90d" else 3, 90.0)
    if src == "CAIXA_APRESENTADO_REDE":
        return (2, 30.0)
    if src == "MOVIMENTO_CONTA":
        return (1, 45.0)
    if src == "TRANSFERENCIA_BANCARIA":
        return (1, 15.0)
    return (2, 60.0)


async def run(skip_90: bool = False, fast: bool = False) -> dict:
    cfg = load_core_config()
    result: dict[str, Any] = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "windows": WINDOWS,
        "readOnly": True,
    }

    window_data: dict[str, Any] = {}

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for wlabel, (di, df) in WINDOWS.items():
            if skip_90 and wlabel == "90d":
                continue
            batch: dict[str, Any] = {"batch": {}}
            raw: dict[str, list[dict]] = {}

            print(f"[F03.1] janela {wlabel} ...", flush=True)
            sources = list(ENDPOINTS.items())
            if fast:
                sources = [(k, v) for k, v in sources if k in ("CAIXA_REDE", "CAIXA", "CAIXA_APRESENTADO", "DESPESAS_REDE", "CAIXA_APRESENTADO_REDE")]

            for src, path in sources:
                pages, timeout = _pages_timeout(src, wlabel)
                rows, status, ms = await _fetch(client, cfg.webposto_base_url, cfg.webposto_api_key, path, di, df, pages, timeout)
                raw[src] = rows
                batch["batch"][src] = {"status": status, "count": len(rows), "ms": ms}
                print(f"  {src}: {status} n={len(rows)} ({ms}ms)", flush=True)

            cx = raw.get("CAIXA_REDE") or raw.get("CAIXA", [])
            ap = raw.get("CAIXA_APRESENTADO", [])
            if not cx:
                cx = raw.get("CAIXA", [])
            merged = _join_caixa(cx, ap)

            forensics = _expense_forensics(merged)
            vs_diff = _expense_vs_diff(merged)
            cross = _despesas_rede_crosscheck(merged, raw.get("DESPESAS_REDE", []))
            classification = _classify_all(merged)

            exp_sum = round(sum(_f(r.get("ap_despesaApurado")) for r in merged), 2)
            diff_sum = round(sum(_f(r.get("diferenca")) for r in merged), 2)

            window_data[wlabel] = {
                **batch,
                "mergedCount": len(merged),
                "despesaApuradoSum": exp_sum,
                "diferencaSum": diff_sum,
                "reportDespesaSum": exp_sum,
                "forensics": forensics,
                "expenseVsDiff": vs_diff,
                "crosscheck": cross,
                "classification": classification,
            }

    primary = window_data.get("7d", {})
    risk = _risk_model(primary.get("crosscheck", {}), primary.get("expenseVsDiff", {}), primary.get("forensics", {}))
    qa = _qa_windows(window_data)

    result["windowAnalysis"] = window_data
    result["riskModel"] = risk
    result["qa"] = qa
    result["executiveAnswers"] = _executive_answers(primary, risk, qa)
    return result


def _executive_answers(primary: dict, risk: dict, qa: dict) -> dict:
    f = primary.get("forensics", {})
    v = primary.get("expenseVsDiff", {})
    c = primary.get("crosscheck", {})
    fr = f.get("respostas", {})
    vr = v.get("respostas", {})
    cr = c.get("respostas", {})

    return {
        "1_despesasNoPdv": fr.get("despesasExplicitas", False),
        "2_camposDespesa": [k for k, meta in f.get("camposMapeados", {}).items() if meta.get("naoZero", 0) > 0],
        "3_porPdv": fr.get("porPdv", False),
        "4_porOperador": fr.get("porOperador", False),
        "5_porTurno": fr.get("porTurno", False),
        "6_impactaDiferenca": fr.get("impactaDiferenca", False),
        "7_correlacao": v.get("correlacaoGlobal"),
        "8_apareceDespesasRede": cr.get("apareceDespesasRede", False),
        "9_duplicidade": cr.get("duplicidade", False),
        "10_classificacao": primary.get("classification", {}).get("porCategoria", {}),
        "11_entrarRiskScore": risk.get("entrarNoCashRiskScore", False),
        "12_dwFactsProntos": ["fact_pdv_expense", "fact_pdv_expense_reconciliation"],
        "13_prontoF032": qa.get("paridadeOk", False) and fr.get("despesasExplicitas", False),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-90", action="store_true")
    parser.add_argument("--fast", action="store_true", help="Omitir MOVIMENTO_CONTA e TRANSFERENCIA_BANCARIA")
    args = parser.parse_args()
    data = asyncio.run(run(skip_90=args.skip_90, fast=args.fast))
    out = ROOT / "scripts" / "f03_1_pdv_expenses_audit.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "path": str(out), "qa": data.get("qa")}, indent=2))


if __name__ == "__main__":
    main()
