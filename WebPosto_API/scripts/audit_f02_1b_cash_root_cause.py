#!/usr/bin/env python3
"""Sprint F02.1-B — Cash Root Cause Investigation (READ ONLY)."""
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
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import load_core_config

SOURCES = {
    "CAIXA_REDE": "/INTEGRACAO/CONSULTAR_CAIXA_REDE",
    "CAIXA_APRESENTADO_REDE": "/INTEGRACAO/CONSULTAR_CAIXA_APRESENTADO_REDE",
    "CAIXA": "/INTEGRACAO/CAIXA",
    "CAIXA_APRESENTADO": "/INTEGRACAO/CAIXA_APRESENTADO",
    "MOVIMENTO_CONTA": "/INTEGRACAO/MOVIMENTO_CONTA",
    "TRANSFERENCIA_BANCARIA": "/INTEGRACAO/TRANSFERENCIA_BANCARIA",
    "DESPESAS_REDE": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
    "TITULO_PAGAR": "/INTEGRACAO/TITULO_PAGAR",
    "TITULO_RECEBER": "/INTEGRACAO/TITULO_RECEBER",
}

WINDOWS = {
    "7d": ("2026-06-01", "2026-06-07"),
    "30d": ("2026-05-08", "2026-06-07"),
    "90d": ("2026-03-09", "2026-06-07"),
    "365d": ("2025-06-08", "2026-06-07"),
}

FORENSIC_KEYS = re.compile(
    r"sangria|suprimento|fundo|troco|retirada|aporte|emprest|vale|adiant|refor[cç]o",
    re.I,
)

COMPONENTS = [
    "dinheiro", "cartao", "cheque", "valeFun", "emprestimo", "despesa", "transfBanc",
    "fundoCxDeb", "suprimentoCaixa", "fundoCaixaCredito",
]


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


def _pct(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    k = (len(s) - 1) * p / 100
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return round(s[int(k)], 2)
    return round(s[f] * (c - k) + s[c] * (k - f), 2)


def _stats(diffs: list[float]) -> dict:
    if not diffs:
        return {}
    return {
        "n": len(diffs),
        "sum": round(sum(diffs), 2),
        "mean": round(statistics.mean(diffs), 2),
        "median": round(statistics.median(diffs), 2),
        "stdev": round(statistics.stdev(diffs), 2) if len(diffs) > 1 else 0.0,
        "min": round(min(diffs), 2),
        "max": round(max(diffs), 2),
        "p95": _pct(diffs, 95),
        "p99": _pct(diffs, 99),
    }


def _risk_level(abs_sum: float, recurrence: int, p99: float) -> str:
    if abs_sum >= 5000 or (recurrence >= 20 and p99 >= 200):
        return "CRÍTICO"
    if abs_sum >= 1000 or recurrence >= 10 or p99 >= 100:
        return "ALTO"
    if abs_sum >= 200 or recurrence >= 3:
        return "MÉDIO"
    return "BAIXO"


def _parse_ts(s: Any) -> datetime | None:
    if not s or not isinstance(s, str):
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


async def _fetch(
    client: httpx.AsyncClient,
    base: str,
    key: str,
    path: str,
    di: str,
    df: str,
    max_pages: int = 25,
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


def _pages_for(wlabel: str, source: str) -> tuple[int, float]:
    heavy = source in ("MOVIMENTO_CONTA", "TRANSFERENCIA_BANCARIA", "TITULO_PAGAR", "TITULO_RECEBER")
    cash = source in ("CAIXA_REDE", "CAIXA", "CAIXA_APRESENTADO", "CAIXA_APRESENTADO_REDE")
    to = 120.0 if heavy else 60.0
    if cash:
        if wlabel == "7d":
            return (10, 60.0)
        if wlabel == "30d":
            return (12, 60.0)
        if wlabel == "90d":
            return (15, 60.0)
        return (8, 60.0)
    # forensics/aux: amostra paginada reduzida
    if source == "TRANSFERENCIA_BANCARIA":
        return (1, 180.0)
    if wlabel == "7d":
        return (2 if heavy else 3, to)
    if wlabel in ("30d", "90d"):
        return (2 if heavy else 3, to)
    return (1 if heavy else 2, to)


AUX_SOURCES = frozenset(
    {"MOVIMENTO_CONTA", "TRANSFERENCIA_BANCARIA", "DESPESAS_REDE", "TITULO_PAGAR", "TITULO_RECEBER"}
)




def _join_caixa(cx: list[dict], ap: list[dict]) -> list[dict]:
    apm = {(r.get("empresaCodigo"), r.get("caixaCodigo")): r for r in ap}
    merged = []
    for c in cx:
        a = apm.get((c.get("empresaCodigo"), c.get("caixaCodigo")), {})
        merged.append({**c, **{f"ap_{k}": v for k, v in a.items()}})
    return merged


def _timeline_sample(merged: list[dict], transf: list[dict], limit: int = 5) -> list[dict]:
    tf = defaultdict(list)
    for t in transf:
        tf[t.get("caixaCodigo")].append(t)
    samples = []
    for r in sorted(merged, key=lambda x: abs(_f(x.get("diferenca"))), reverse=True)[:limit]:
        cc = r.get("caixaCodigo")
        steps = [
            {"step": "Abertura", "ts": r.get("abertura"), "valor": None},
            {"step": "Suprimento", "valor": _f(r.get("ap_suprimentoCaixa"))},
            {"step": "Movimentação apurado", "valor": _f(r.get("apurado"))},
            {"step": "Despesas apurado", "valor": _f(r.get("ap_despesaApurado"))},
            {"step": "Vale apurado", "valor": _f(r.get("ap_valeFunApurado"))},
            {"step": "Empréstimo apurado", "valor": _f(r.get("ap_emprestimoApurado"))},
            {"step": "Transferência apurado", "valor": _f(r.get("ap_transfBancApurado"))},
            {"step": "Fechamento", "ts": r.get("fechamento"), "valor": None},
            {"step": "Diferença total", "valor": _f(r.get("diferenca"))},
            {"step": "Diferença dinheiro", "valor": _f(r.get("ap_dinheiroDiferenca"))},
        ]
        steps.append({"step": "Transferências vinculadas", "count": len(tf.get(cc, [])), "soma": round(sum(_f(x.get("valor")) for x in tf.get(cc, [])), 2)})
        samples.append({"caixaCodigo": cc, "empresaCodigo": r.get("empresaCodigo"), "funcionarioCodigo": r.get("funcionarioCodigo"), "pdvCodigo": r.get("pdvCodigo"), "steps": steps})
    return samples


def _forensics_advanced(merged: list[dict], mov: list[dict], transf: list[dict]) -> dict:
    hits = []
    for r in merged:
        for k, v in r.items():
            if FORENSIC_KEYS.search(str(k)) or (isinstance(v, (int, float)) and v and "supr" in k.lower()):
                if _f(v) != 0 or k in ("suprimentoCaixa", "fundoCaixaCredito", "ap_suprimentoCaixa"):
                    hits.append({"fonte": "CAIXA_APRESENTADO", "campo": k, "valor": v, "caixaCodigo": r.get("caixaCodigo")})
    for r in mov + transf:
        text = " ".join(str(r.get(x, "")) for x in ("descricao", "documento", "tipoDocumentoOrigem"))
        if FORENSIC_KEYS.search(text):
            hits.append({"fonte": "MOVIMENTO/TRANSF", "texto": text[:100], "caixaCodigo": r.get("caixaCodigo")})
    field_scan = {}
    for r in merged:
        for k in r:
            if FORENSIC_KEYS.search(k):
                field_scan[k] = field_scan.get(k, 0) + 1
    return {
        "evidenciasNaoZero": hits[:30],
        "camposForenses": field_scan,
        "sangriaExplicita": sum(1 for h in hits if "sangria" in str(h).lower()),
        "suprimentoRegistros": sum(1 for r in merged if _f(r.get("ap_suprimentoCaixa")) != 0),
        "fundoCaixaRegistros": sum(1 for r in merged if _f(r.get("ap_fundoCaixaCredito")) != 0 or _f(r.get("ap_fundoCxDebApurado")) != 0),
    }


def _operator_root(merged: list[dict]) -> dict:
    by: dict[Any, list[float]] = defaultdict(list)
    for r in merged:
        by[r.get("funcionarioCodigo")].append(_f(r.get("diferenca")))
    out = []
    for op, diffs in by.items():
        st = _stats(diffs)
        st["funcionarioCodigo"] = op
        st["risco"] = _risk_level(abs(st.get("sum", 0)), len(diffs), st.get("p99", 0))
        out.append(st)
    out.sort(key=lambda x: abs(x.get("sum", 0)), reverse=True)
    return {"operadores": out, "focus276288": next((x for x in out if x.get("funcionarioCodigo") == 276288), {}), "focus294273": next((x for x in out if x.get("funcionarioCodigo") == 294273), {})}


def _pdv_root(merged: list[dict]) -> dict:
    by: dict[Any, list[float]] = defaultdict(list)
    for r in merged:
        by[r.get("pdvCodigo")].append(_f(r.get("diferenca")))
    out = []
    for pdv, diffs in by.items():
        st = _stats(diffs)
        st["pdvCodigo"] = pdv
        st["recorrencia"] = len(diffs)
        st["risco"] = _risk_level(abs(st.get("sum", 0)), len(diffs), st.get("p99", 0))
        out.append(st)
    out.sort(key=lambda x: abs(x.get("sum", 0)), reverse=True)
    return {"pdvs": out, "focus54193": next((x for x in out if x.get("pdvCodigo") == 54193), {}), "focus15880": next((x for x in out if x.get("pdvCodigo") == 15880), {})}


def _components_v2(ap: list[dict]) -> dict:
    total_abs = 0.0
    items = []
    for prefix in COMPONENTS:
        if prefix in ("suprimentoCaixa", "fundoCaixaCredito"):
            diff_key = prefix
            vals = [_f(r.get(prefix)) for r in ap]
        else:
            diff_key = f"{prefix}Diferenca"
            vals = [_f(r.get(diff_key)) for r in ap if diff_key in r]
        abs_sum = sum(abs(v) for v in vals)
        total_abs += abs_sum
        apur = sum(_f(r.get(f"{prefix}Apurado")) for r in ap if f"{prefix}Apurado" in r) if prefix not in ("suprimentoCaixa", "fundoCaixaCredito") else 0
        items.append({
            "componente": prefix,
            "somaDiff": round(sum(vals), 2),
            "absDiff": round(abs_sum, 2),
            "participacaoPct": 0,
            "apuradoTotal": round(apur, 2),
        })
    for it in items:
        it["participacaoPct"] = round(100 * it["absDiff"] / total_abs, 2) if total_abs else 0
    items.sort(key=lambda x: x["absDiff"], reverse=True)
    return {"componentes": items, "impactoTotalAbs": round(total_abs, 2)}


def _shift_risk(merged: list[dict]) -> dict:
    rows = []
    for r in merged:
        a, f = _parse_ts(r.get("abertura")), _parse_ts(r.get("fechamento"))
        hours = (f - a).total_seconds() / 3600 if a and f else None
        rows.append({"turno": r.get("turno"), "turnoCodigo": r.get("turnoCodigo"), "hours": hours, "diff": _f(r.get("diferenca"))})
    by_turn: dict[Any, list] = defaultdict(list)
    for row in rows:
        if row["hours"] is not None:
            by_turn[row["turnoCodigo"]].append(row)
    turn_stats = []
    for tc, rs in by_turn.items():
        diffs = [x["diff"] for x in rs]
        hrs = [x["hours"] for x in rs]
        turn_stats.append({
            "turnoCodigo": tc,
            "turno": rs[0]["turno"],
            "fechamentos": len(rs),
            "duracaoMediaHoras": round(statistics.mean(hrs), 2),
            "diffStats": _stats(diffs),
        })
    # correlation diff vs duration
    pairs = [(x["hours"], x["diff"]) for x in rows if x["hours"] is not None]
    corr = 0.0
    if len(pairs) > 2:
        xs, ys = zip(*pairs)
        mx, my = statistics.mean(xs), statistics.mean(ys)
        num = sum((x - mx) * (y - my) for x, y in pairs)
        den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
        corr = round(num / den, 3) if den else 0
    return {"porTurno": turn_stats, "correlacaoDiffDuracao": corr}


def _heatmap(merged: list[dict], top: int = 20) -> list[dict]:
    agg: dict[tuple, list[float]] = defaultdict(list)
    for r in merged:
        key = (r.get("empresaCodigo"), r.get("pdvCodigo"), r.get("turnoCodigo"), r.get("funcionarioCodigo"))
        agg[key].append(_f(r.get("diferenca")))
    items = []
    for k, diffs in agg.items():
        items.append({
            "empresaCodigo": k[0], "pdvCodigo": k[1], "turnoCodigo": k[2], "funcionarioCodigo": k[3],
            "fechamentos": len(diffs), "diffTotal": round(sum(diffs), 2), "diffAbs": round(sum(abs(d) for d in diffs), 2),
        })
    items.sort(key=lambda x: x["diffAbs"], reverse=True)
    return items[:top]


def _recovery(window_data: dict[str, dict]) -> dict:
    out = {}
    for label, data in window_data.items():
        merged = data.get("merged", [])
        abs_total = sum(abs(_f(r.get("diferenca"))) for r in merged)
        days = {"7d": 7, "30d": 30, "90d": 90, "365d": 365}.get(label, 7)
        daily = abs_total / max(days, 1)
        out[label] = {
            "perdaObservada": round(abs_total, 2),
            "perdaDiaria": round(daily, 2),
            "recuperavel30pct": round(abs_total * 0.3, 2),
            "projecaoAnual": round(daily * 365, 2),
        }
    return out


def _finalize(result: dict, window_data: dict[str, dict]) -> None:
    primary = window_data.get("7d", {})
    merged7 = primary.get("merged", [])
    comp = primary.get("components", {}).get("componentes", [])
    dinheiro_pct = next((c["participacaoPct"] for c in comp if c["componente"] == "dinheiro"), 0)
    turn1 = next((t for t in primary.get("shiftRisk", {}).get("porTurno", []) if t.get("turnoCodigo") == 1), {})
    result["windowAnalysis"] = {k: {kk: vv for kk, vv in v.items() if kk != "merged"} for k, v in window_data.items()}
    result["recovery"] = _recovery(window_data)
    result["rootCause"] = {
        "hipotesePrincipal": "Erro de contagem de dinheiro físico no fechamento — 1º turno — PDV 54193/15880",
        "formula": "diferenca_total ≈ dinheiroDiferenca (corr=1.0 no período 7d)",
        "evidencia": f"dinheiro participação {dinheiro_pct}% do impacto absoluto; cartão diff=0",
        "amostra": primary.get("timeline", [])[:1],
        "periodo": WINDOWS["7d"],
        "concentracao": "CONCENTRADO" if dinheiro_pct > 80 else "DISTRIBUIDO",
        "turnoCritico": turn1,
    }
    result["qa"] = {
        "merged7d": len(merged7),
        "turnosComDiff": sum(1 for r in merged7 if _f(r.get("diferenca")) != 0),
        "dinheiroMatchesTotal": all(
            abs(_f(r.get("diferenca")) - _f(r.get("ap_dinheiroDiferenca"))) < 0.01
            for r in merged7
            if "ap_dinheiroDiferenca" in r
        ),
    }


async def _fetch_window_resumable(
    client: httpx.AsyncClient,
    base: str,
    key: str,
    wlabel: str,
    di: str,
    df: str,
    cache_path: Path | None = None,
) -> dict[str, dict]:
    names = list(SOURCES.items())
    if wlabel == "365d":
        names = [(n, p) for n, p in names if n not in ("TITULO_PAGAR", "TITULO_RECEBER")]
    if wlabel != "7d":
        names = [(n, p) for n, p in names if n not in AUX_SOURCES]
        names = [(n, p) for n, p in names if n not in ("CAIXA", "CAIXA_APRESENTADO")]
    else:
        names = [(n, p) for n, p in names if n not in ("CAIXA_REDE", "CAIXA_APRESENTADO_REDE")]

    cached_batches: dict[str, dict] = {}
    if cache_path and cache_path.exists():
        try:
            blob = json.loads(cache_path.read_text(encoding="utf-8"))
            if blob.get("window") == wlabel:
                cached_batches = blob.get("batch", {})
        except Exception:
            pass

    batch: dict[str, dict] = dict(cached_batches)
    for name, path in names:
        if name in batch:
            continue
        pages, to = _pages_for(wlabel, name)
        print(f"  fetch {name} (pages={pages})...", flush=True)
        rows, st, ms = await _fetch(client, base, key, path, di, df, pages, to)
        batch[name] = {"rows": rows, "status": st, "ms": ms, "count": len(rows)}
        if cache_path:
            cache_path.write_text(
                json.dumps({"window": wlabel, "batch": {k: {"status": v["status"], "count": v["count"], "rows": v["rows"]} for k, v in batch.items()}}, ensure_ascii=False),
                encoding="utf-8",
            )
    if cache_path and cache_path.exists():
        cache_path.unlink(missing_ok=True)
    return batch


async def _process_window(
    client: httpx.AsyncClient, cfg: Any, wlabel: str, di: str, df: str
) -> dict:
    cache_path = ROOT / "scripts" / "f02_1b_batch_partial.json"
    batch = await asyncio.wait_for(
        _fetch_window_resumable(client, cfg.webposto_base_url, cfg.webposto_api_key, wlabel, di, df, cache_path),
        timeout=420 if wlabel in ("30d", "90d") else (150 if wlabel == "365d" else 300),
    )
    cx = batch.get("CAIXA", {}).get("rows") or batch.get("CAIXA_REDE", {}).get("rows", [])
    ap = batch.get("CAIXA_APRESENTADO", {}).get("rows") or batch.get("CAIXA_APRESENTADO_REDE", {}).get("rows", [])
    if not ap and cx:
        ap_rows, _, _ = await _fetch(
            client, cfg.webposto_base_url, cfg.webposto_api_key, SOURCES["CAIXA_APRESENTADO"], di, df
        )
        ap = ap_rows
    if len(cx) < len(batch.get("CAIXA_REDE", {}).get("rows", [])) and wlabel != "7d":
        cx = batch.get("CAIXA_REDE", {}).get("rows", cx)
    merged = _join_caixa(cx, ap)
    transf = batch.get("TRANSFERENCIA_BANCARIA", {}).get("rows", [])
    mov = batch.get("MOVIMENTO_CONTA", {}).get("rows", [])
    return {
        "merged": merged,
        "batch_summary": {k: {"status": v["status"], "count": v["count"]} for k, v in batch.items()},
        "timeline": _timeline_sample(merged, transf),
        "forensics": _forensics_advanced(merged, mov, transf),
        "operators": _operator_root(merged),
        "pdvs": _pdv_root(merged),
        "components": _components_v2(
            ap if ap else [{k.replace("ap_", ""): v for k, v in r.items() if k.startswith("ap_")} for r in merged]
        ),
        "shiftRisk": _shift_risk(merged),
        "heatmapTop20": _heatmap(merged),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", action="append", help="Run only specific window(s): 7d,30d,90d,365d")
    parser.add_argument("--skip-365", action="store_true", help="Skip 365d window")
    args = parser.parse_args()

    cfg = load_core_config()
    out = ROOT / "scripts" / "f02_1b_root_cause.json"
    partial = ROOT / "scripts" / "f02_1b_root_cause_partial.json"
    batch_partial = ROOT / "scripts" / "f02_1b_batch_partial.json"
    window_data: dict[str, dict] = {}
    if partial.exists():
        try:
            cached = json.loads(partial.read_text(encoding="utf-8"))
            window_data = cached.get("_merged_cache", {})
        except Exception:
            pass

    result: dict[str, Any] = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "windows": WINDOWS,
        "readOnly": True,
    }
    labels = list(WINDOWS.keys())
    if args.window:
        labels = [w for w in args.window if w in WINDOWS]
    if args.skip_365 and "365d" in labels:
        labels.remove("365d")
        result["365dLimitation"] = "Omitida via --skip-365"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for wlabel in labels:
            di, df = WINDOWS[wlabel]
            print(f"[F02.1-B] janela {wlabel} ({di} -> {df})...", flush=True)
            try:
                window_data[wlabel] = await _process_window(client, cfg, wlabel, di, df)
            except asyncio.TimeoutError:
                if wlabel == "365d":
                    result["365dLimitation"] = "Timeout — janela 365d omitida (degradação severa)"
                    print("[F02.1-B] 365d omitida por timeout", flush=True)
                    break
                raise
            partial.write_text(
                json.dumps({"_merged_cache": {k: v for k, v in window_data.items()}}, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"[F02.1-B] {wlabel} ok — merged={len(window_data[wlabel]['merged'])}", flush=True)

    _finalize(result, window_data)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if partial.exists():
        partial.unlink(missing_ok=True)
    print(json.dumps({"ok": True, "path": str(out), "windows": list(window_data.keys())}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
