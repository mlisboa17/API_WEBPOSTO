#!/usr/bin/env python3
"""D01 — Live Operational Join Probe (READ ONLY)."""
from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from src.core.config import load_core_config
from src.gateway.webposto_client import WebPostoClient

WINDOWS = {
    "7d": ("2026-06-02", "2026-06-08"),
    "30d": ("2026-05-09", "2026-06-08"),
    "90d": ("2026-03-10", "2026-06-08"),
}
TARGET_EMPRESA = 5555  # AP CASA CAIADA
PRESTACAO_DATE = "2026-06-08"
PRESTACAO_TURNO = 1

ENDPOINTS: list[tuple[str, str | None]] = [
    ("caixa_rede", "caixa"),
    ("caixa", None),
    ("caixa_apresentado_rede", "caixa_apresentado"),
    ("caixa_apresentado", None),
    ("venda", None),
    ("venda_item", None),
    ("venda_forma_pagamento_rede", "venda_forma_pagamento"),
    ("venda_forma_pagamento", None),
    ("abastecimento", None),
    ("nfce", None),
    ("movimento_conta", None),
    ("transferencia_bancaria", None),
]

FIELD_MAP: dict[str, list[str]] = {
    "payment_form": [
        "vendaCodigo", "caixaCodigo", "turnoCodigo", "empresaCodigo",
        "formaPagamentoCodigo", "nomeFormaPagamento", "administradoraCodigo",
        "valorPagamento", "dataMovimento", "funcionarioCodigo", "pdvCodigo",
    ],
    "sale": [
        "vendaCodigo", "caixaCodigo", "funcionarioCodigo", "empresaCodigo",
        "pdvCodigo", "dataMovimento", "dataHora", "cancelada", "troco", "totalVenda",
    ],
    "sale_item": [
        "vendaCodigo", "produtoCodigo", "funcionarioCodigo", "bicoCodigo",
        "totalDesconto", "totalVenda", "quantidade", "tanqueCodigo", "produtoLmcCodigo",
    ],
    "fueling": [
        "abastecimentoCodigo", "vendaItemCodigo", "codigoFrentista", "codigoBico",
        "codigoProduto", "quantidade", "valorTotal", "encerrante", "empresaCodigo",
    ],
    "nfce": [
        "vendaCodigo", "nfceCodigo", "situacao", "dataEmissao", "empresaCodigo",
        "numeroDocumento", "serieDocumento",
    ],
}


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "data", "items"):
            val = payload.get(key)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
    return []


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0")


def _norm_date(row: dict[str, Any]) -> str:
    for k in ("dataMovimento", "dataHora", "data", "dataEmissao", "dataFiscal"):
        v = row.get(k)
        if v:
            return str(v)[:10]
    return ""


def field_discovery(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, Any]:
    total = len(rows)
    out: dict[str, Any] = {"totalRows": total, "fields": {}}
    for f in fields:
        non_null = sum(1 for r in rows if r.get(f) not in (None, "", "0", 0))
        samples = []
        for r in rows:
            v = r.get(f)
            if v not in (None, "", "0", 0):
                samples.append(v)
                if len(samples) >= 3:
                    break
        out["fields"][f] = {
            "exists": non_null > 0,
            "coveragePct": round(100 * non_null / total, 2) if total else 0.0,
            "samples": samples[:3],
        }
    out["allKeys"] = sorted({k for r in rows for k in r.keys()}) if rows else []
    return out


def join_coverage(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    left_keys: tuple[str, ...],
    right_keys: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    right_keys = right_keys or left_keys
    idx: set[tuple[Any, ...]] = set()
    for r in right:
        key = tuple(r.get(k) for k in right_keys)
        if all(v is not None for v in key):
            idx.add(key)
    if not left:
        return {"leftCount": 0, "matched": 0, "coveragePct": 0.0, "confidence": "LOW"}
    matched = 0
    for r in left:
        key = tuple(r.get(k) for k in left_keys)
        if all(v is not None for v in key) and key in idx:
            matched += 1
    pct = round(100 * matched / len(left), 2)
    conf = "HIGH" if pct >= 90 else "MEDIUM" if pct >= 70 else "LOW"
    return {"leftCount": len(left), "matched": matched, "coveragePct": pct, "confidence": conf}


async def fetch_day_empresa(
    client: WebPostoClient,
    key: str,
    day: str,
    empresa: int,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in range(max_pages):
        params: dict[str, Any] = {"dataInicial": day, "dataFinal": day}
        if page:
            params["pagina"] = page + 1
        resp = await client.call_endpoint(key, params=params)
        if not resp.success:
            break
        chunk = _rows(resp.data)
        if not chunk:
            break
        rows.extend(chunk)
        if isinstance(resp.data, dict) and resp.data.get("ultimaPagina", True):
            break
    return [r for r in rows if int(r.get("empresaCodigo") or 0) == empresa]


async def fetch_endpoint(
    client: WebPostoClient,
    key: str,
    di: str,
    df: str,
    max_pages: int,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    params: dict[str, Any] = {"dataInicial": di, "dataFinal": df}
    all_rows: list[dict[str, Any]] = []
    pages = 0
    timeout = False
    status = 0
    error = None
    ultima = True
    latencies: list[float] = []

    for page in range(max_pages):
        page_params = {**params, "pagina": page + 1} if page else params
        p0 = time.perf_counter()
        try:
            resp = await asyncio.wait_for(
                client.call_endpoint(key, params=page_params),
                timeout=120.0,
            )
        except asyncio.TimeoutError:
            timeout = True
            error = "timeout_page"
            break
        latencies.append(round((time.perf_counter() - p0) * 1000, 2))
        pages += 1
        if not resp.success:
            error = resp.error.message if resp.error else "fail"
            status = resp.error.status if resp.error else 0
            break
        status = 200
        chunk = _rows(resp.data)
        if not chunk:
            break
        all_rows.extend(chunk)
        if isinstance(resp.data, dict):
            ultima = bool(resp.data.get("ultimaPagina", True))
            if ultima:
                break
        else:
            break

    elapsed = round(time.perf_counter() - t0, 2)
    truncated = not ultima and pages >= max_pages
    return {
        "key": key,
        "status": status,
        "error": error,
        "timeout": timeout,
        "truncated": truncated,
        "pages": pages,
        "count": len(all_rows),
        "hasData": len(all_rows) > 0,
        "latencyMsAvg": round(statistics.mean(latencies), 2) if latencies else 0,
        "latencyMsMax": max(latencies) if latencies else 0,
        "elapsedSec": elapsed,
        "rows": all_rows,
    }


async def probe_window(
    client: WebPostoClient,
    label: str,
    di: str,
    df: str,
    max_pages: int,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    fetched: dict[str, dict[str, Any]] = {}
    for primary, fallback in ENDPOINTS:
        result = await fetch_endpoint(client, primary, di, df, max_pages)
        if not result["hasData"] and fallback:
            fb = await fetch_endpoint(client, fallback, di, df, max_pages)
            if fb["hasData"] or fb["status"] == 200:
                fb["usedFallback"] = primary
                result = fb
        fetched[primary.split("_rede")[0] if "_rede" in primary else primary] = result

    def rows(key: str) -> list[dict[str, Any]]:
        return fetched.get(key, {}).get("rows") or []

    caixa = rows("caixa") or rows("caixa_rede")
    ap = rows("caixa_apresentado") or rows("caixa_apresentado_rede")
    venda = rows("venda")
    venda_item = rows("venda_item")
    vfp = rows("venda_forma_pagamento") or rows("venda_forma_pagamento_rede")
    abast = rows("abastecimento")
    nfce = rows("nfce")

    # Empresa filter for deep analysis
    def filtrar(rs: list[dict], emp: int) -> list[dict]:
        return [r for r in rs if int(r.get("empresaCodigo") or 0) == emp]

    caixa_e = filtrar(caixa, TARGET_EMPRESA)
    venda_e = filtrar(venda, TARGET_EMPRESA)
    vfp_e = filtrar(vfp, TARGET_EMPRESA)
    vi_e = filtrar(venda_item, TARGET_EMPRESA)
    ab_e = filtrar(abast, TARGET_EMPRESA)
    nf_e = filtrar(nfce, TARGET_EMPRESA)

    joins = [
        {"a": "VENDA_FORMA_PAGAMENTO", "b": "VENDA", "keys": ("empresaCodigo", "vendaCodigo"),
         **join_coverage(vfp, venda, ("empresaCodigo", "vendaCodigo"))},
        {"a": "VENDA", "b": "CAIXA", "keys": ("empresaCodigo", "caixaCodigo"),
         **join_coverage(venda, caixa, ("empresaCodigo", "caixaCodigo"))},
        {"a": "VENDA_ITEM", "b": "VENDA", "keys": ("empresaCodigo", "vendaCodigo"),
         **join_coverage(venda_item, venda, ("empresaCodigo", "vendaCodigo"))},
        {"a": "ABASTECIMENTO", "b": "VENDA_ITEM", "keys": ("empresaCodigo", "vendaItemCodigo"),
         **join_coverage(abast, venda_item, ("empresaCodigo", "vendaItemCodigo"))},
        {"a": "NFCE", "b": "VENDA", "keys": ("empresaCodigo", "vendaCodigo"),
         **join_coverage(nfce, venda, ("empresaCodigo", "vendaCodigo"))},
    ]

    # VFP → CAIXA via VENDA bridge
    venda_idx = {(r.get("empresaCodigo"), r.get("vendaCodigo")): r for r in venda}
    vfp_caixa_match = 0
    for r in vfp:
        v = venda_idx.get((r.get("empresaCodigo"), r.get("vendaCodigo")))
        if v and v.get("caixaCodigo"):
            vfp_caixa_match += 1
    vfp_caixa_pct = round(100 * vfp_caixa_match / len(vfp), 2) if vfp else 0.0

    # Enrich VFP with caixa/funcionario/pdv from VENDA
    vfp_enriched = []
    for r in vfp:
        v = venda_idx.get((r.get("empresaCodigo"), r.get("vendaCodigo"))) or {}
        caixa_row = next(
            (c for c in caixa if c.get("caixaCodigo") == v.get("caixaCodigo")
             and c.get("empresaCodigo") == v.get("empresaCodigo")),
            {},
        )
        vfp_enriched.append({**r, "_caixaCodigo": v.get("caixaCodigo"), "_funcionarioCodigo": v.get("funcionarioCodigo"),
                             "_pdvCodigo": caixa_row.get("pdvCodigo")})

    payment_discovery = field_discovery(vfp, FIELD_MAP["payment_form"])
    payment_discovery["viaVenda"] = {
        "caixaCodigo": {"coveragePct": vfp_caixa_pct, "exists": vfp_caixa_match > 0},
        "funcionarioCodigo": field_discovery(
            [{"funcionarioCodigo": r.get("_funcionarioCodigo")} for r in vfp_enriched],
            ["funcionarioCodigo"],
        )["fields"]["funcionarioCodigo"],
        "pdvCodigo": field_discovery(
            [{"pdvCodigo": r.get("_pdvCodigo")} for r in vfp_enriched],
            ["pdvCodigo"],
        )["fields"]["pdvCodigo"],
    }

    sale_discovery = field_discovery(venda, FIELD_MAP["sale"])
    caixa_idx_full = {(c.get("empresaCodigo"), c.get("caixaCodigo")): c for c in caixa}
    venda_pdv = []
    for r in venda:
        c = caixa_idx_full.get((r.get("empresaCodigo"), r.get("caixaCodigo"))) or {}
        venda_pdv.append({"pdvCodigo": c.get("pdvCodigo")})
    sale_discovery["viaCaixa"] = {
        "pdvCodigo": field_discovery(venda_pdv, ["pdvCodigo"])["fields"]["pdvCodigo"],
    }
    sale_item_discovery = field_discovery(venda_item, FIELD_MAP["sale_item"])
    fueling_discovery = field_discovery(abast, FIELD_MAP["fueling"])
    nfce_discovery = field_discovery(nfce, FIELD_MAP["nfce"])

    # Prestacao reconstruction (5555, target date or último dia útil na janela)
    probe_date = PRESTACAO_DATE if di <= PRESTACAO_DATE <= df else df

    # Fetch dedicado dia/empresa para reconstrução (evita viés de paginação global)
    day_venda = await fetch_day_empresa(client, "venda", probe_date, TARGET_EMPRESA, max_pages=5)
    day_vfp = await fetch_day_empresa(client, "venda_forma_pagamento", probe_date, TARGET_EMPRESA, max_pages=5)
    day_vi = await fetch_day_empresa(client, "venda_item", probe_date, TARGET_EMPRESA, max_pages=5)
    day_abast = await fetch_day_empresa(client, "abastecimento", probe_date, TARGET_EMPRESA, max_pages=5)
    day_caixa = await fetch_day_empresa(client, "caixa", probe_date, TARGET_EMPRESA, max_pages=3)

    caixa_day = day_caixa or [r for r in caixa_e if _norm_date(r) == probe_date]
    if not caixa_day:
        dates = sorted({_norm_date(r) for r in caixa_e if _norm_date(r)}, reverse=True)
        probe_date = dates[0] if dates else probe_date
        caixa_day = [r for r in caixa_e if _norm_date(r) == probe_date]
    turno_rows = [
        r for r in caixa_day
        if str(r.get("turno") or "").strip().startswith("1")
        or str(r.get("turnoCodigo") or "") in {"1", "01"}
        or (not caixa_day and False)
    ] or caixa_day[:1]
    venda_day = day_venda or [r for r in venda_e if _norm_date(r) == probe_date]
    vfp_day = day_vfp or [r for r in vfp_e if _norm_date(r) == probe_date]

    by_forma = Counter()
    for r in vfp_day:
        by_forma[str(r.get("nomeFormaPagamento") or r.get("formaPagamentoCodigo"))] += float(_dec(r.get("valorPagamento")))

    by_func = Counter()
    for r in venda_day:
        cancelled = str(r.get("cancelada") or "").lower() in {"1", "true", "s", "sim", "cancelada"}
        if not cancelled:
            op = r.get("funcionarioCodigo")
            by_func[str(op)] += float(_dec(r.get("totalVenda")))

    by_pdv = Counter()
    for r in venda_day:
        c = caixa_idx_full.get((r.get("empresaCodigo"), r.get("caixaCodigo"))) or {}
        by_pdv[str(c.get("pdvCodigo"))] += float(_dec(r.get("totalVenda")))

    cancel_count = sum(1 for r in venda_day if r.get("cancelada"))
    troco_total = sum(float(_dec(r.get("troco"))) for r in venda_day)
    desconto_total = sum(float(_dec(r.get("totalDesconto"))) for r in (day_vi or vi_e) if _norm_date(r) == probe_date)

    combustivel_val = Decimal("0")
    produto_val = Decimal("0")
    vi_day = day_vi or [r for r in vi_e if _norm_date(r) == probe_date]
    for r in vi_day:
        if r.get("bicoCodigo") or r.get("tanqueCodigo") or r.get("produtoLmcCodigo"):
            combustivel_val += _dec(r.get("totalVenda"))
        else:
            produto_val += _dec(r.get("totalVenda"))

    abast_day = day_abast or [
        r for r in ab_e if _norm_date(r) == probe_date or str(r.get("dataFiscal", ""))[:10] == probe_date
    ]
    by_frentista = Counter()
    for r in abast_day:
        by_frentista[str(r.get("codigoFrentista"))] += float(_dec(r.get("valorTotal")))

    total_venda_day = sum(float(_dec(r.get("totalVenda"))) for r in venda_day if not r.get("cancelada"))
    participacao = {
        k: round(100 * v / total_venda_day, 2) if total_venda_day else 0
        for k, v in by_func.items()
    }

    reconstruction_layers = {
        "formaPagamento": len(by_forma) > 0,
        "porFuncionario": len(by_func) > 0,
        "porPdv": len(by_pdv) > 0,
        "porTurno": len(turno_rows) > 0,
        "combustivelProduto": float(combustivel_val + produto_val) > 0,
        "trocoCancelamentos": troco_total > 0 or cancel_count > 0,
        "descontos": desconto_total > 0,
        "participacaoPct": len(participacao) > 1,
    }
    recon_score = round(100 * sum(reconstruction_layers.values()) / len(reconstruction_layers), 2)

    performance = {
        k: {kk: vv for kk, vv in v.items() if kk != "rows"}
        for k, v in fetched.items()
    }

    elapsed = round(time.perf_counter() - t0, 2)
    return {
        "window": label,
        "periodo": {"inicio": di, "fim": df},
        "elapsedSec": elapsed,
        "truncatedAny": any(v.get("truncated") for v in fetched.values()),
        "performance": performance,
        "paymentFormDiscovery": payment_discovery,
        "saleDiscovery": sale_discovery,
        "saleItemDiscovery": sale_item_discovery,
        "fuelingDiscovery": fueling_discovery,
        "nfceDiscovery": nfce_discovery,
        "joinMatrix": joins,
        "vfpToCaixaViaVendaPct": vfp_caixa_pct,
        "prestacaoProbe": {
            "targetEmpresa": TARGET_EMPRESA,
            "targetDate": PRESTACAO_DATE,
            "probeDateUsed": probe_date,
            "dateInWindow": di <= PRESTACAO_DATE <= df,
            "caixaTurnos": len(turno_rows),
            "vendasDia": len(venda_day),
            "vfpDia": len(vfp_day),
            "fetchDedicadoDia": True,
            "byFormaPagamento": dict(by_forma),
            "byFuncionarioValor": dict(by_func),
            "byPdvValor": dict(by_pdv),
            "participacaoPct": participacao,
            "trocoTotal": troco_total,
            "cancelamentos": cancel_count,
            "descontoTotal": desconto_total,
            "combustivelValor": float(combustivel_val),
            "produtoValor": float(produto_val),
            "abastecimentosDia": len(abast_day),
            "byFrentista": dict(by_frentista),
            "reconstructionLayers": reconstruction_layers,
            "reconstructionCoveragePct": recon_score,
        },
        "operatorProductivity": {
            "valorPorFuncionario": dict(by_func),
            "abastecimentosPorFrentista": dict(Counter(str(r.get("codigoFrentista")) for r in abast_day)),
            "combustivelPorFrentista": dict(by_frentista),
            "participacaoCalculada": participacao,
            "participacaoPrestacaoDisponivel": False,
        },
        "counts": {
            "caixa": len(caixa), "venda": len(venda), "venda_item": len(venda_item),
            "vfp": len(vfp), "abastecimento": len(abast), "nfce": len(nfce),
        },
    }


async def main() -> None:
    only = os.environ.get("D01_WINDOW")
    windows = {only: WINDOWS[only]} if only and only in WINDOWS else WINDOWS
    max_pages = int(os.environ.get("D01_MAX_PAGES", "25"))

    client = WebPostoClient(load_core_config())
    results: dict[str, dict] = {}
    for label, (di, df) in windows.items():
        print(f"D01 probe {label} {di}..{df} max_pages={max_pages}")
        try:
            results[label] = await probe_window(client, label, di, df, max_pages)
        except Exception as exc:
            results[label] = {"window": label, "error": str(exc)[:300]}
        print(f"  done {label} elapsed={results[label].get('elapsedSec')}s")

    # Executive from best window (prefer 7d, else 30d)
    ref = results.get("7d") or results.get("30d") or next(iter(results.values()), {})
    joins = ref.get("joinMatrix") or []
    join_ok = any(
        j.get("a") == "VENDA_FORMA_PAGAMENTO" and j.get("coveragePct", 0) >= 50
        for j in joins
    ) and any(j.get("a") == "VENDA" and j.get("b") == "CAIXA" and j.get("coveragePct", 0) >= 50 for j in joins)

    pf = ref.get("paymentFormDiscovery") or {}
    pf_fields = pf.get("fields") or {}
    via = pf.get("viaVenda") or {}
    sd = ref.get("saleDiscovery") or {}
    sd_fields = (sd.get("fields") or {})
    si = ref.get("saleItemDiscovery") or {}
    si_fields = (si.get("fields") or {})
    fd = ref.get("fuelingDiscovery") or {}
    fd_fields = (fd.get("fields") or {})
    nd = ref.get("nfceDiscovery") or {}
    nd_fields = (nd.get("fields") or {})
    prest = ref.get("prestacaoProbe") or {}
    layers = prest.get("reconstructionLayers") or {}
    recon_pct = prest.get("reconstructionCoveragePct", 0)

    exclusive_prestacao = [
        "funcionarioNome", "participacaoIndividual (oficial UI)", "produtividadeFuncionario",
        "fundoCaixa", "layout nominal turno",
    ]

    executive = {
        "1_vfp_vendaCodigo": pf_fields.get("vendaCodigo", {}).get("exists"),
        "2_vfp_caixaCodigo": via.get("caixaCodigo", {}).get("exists"),
        "3_vfp_turnoCodigo": pf_fields.get("turnoCodigo", {}).get("exists"),
        "4_venda_funcionarioCodigo": sd_fields.get("funcionarioCodigo", {}).get("exists"),
        "5_venda_pdvCodigo": (sd.get("viaCaixa") or {}).get("pdvCodigo", {}).get("exists"),
        "6_vendaItem_funcionarioCodigo": si_fields.get("funcionarioCodigo", {}).get("exists"),
        "7_abast_codigoFrentista": fd_fields.get("codigoFrentista", {}).get("exists"),
        "8_abast_liga_venda": next((j.get("coveragePct", 0) >= 30 for j in joins if j.get("a") == "ABASTECIMENTO"), False),
        "9_nfce_liga_venda": nd_fields.get("vendaCodigo", {}).get("exists"),
        "10_recon_forma_pagamento": layers.get("formaPagamento"),
        "11_recon_venda_funcionario": layers.get("porFuncionario"),
        "12_recon_produtividade": layers.get("participacaoPct"),
        "13_recon_combustivel_produto": layers.get("combustivelProduto"),
        "14_recon_troco_cancel": layers.get("trocoCancelamentos"),
        "15_pdf_necessario": True,
        "16_campos_exclusivos_prestacao": exclusive_prestacao,
        "17_fontes_primarias_f04": ["VENDA", "VENDA_ITEM", "VENDA_FORMA_PAGAMENTO", "CAIXA", "ABASTECIMENTO"],
        "18_fontes_auxiliares_f04": ["NFCE", "MOVIMENTO_CONTA", "CAIXA_APRESENTADO", "DESPESAS_REDE"],
        "19_cobertura_reconstrucao_pct": recon_pct,
        "20_f04_api_ou_parser": None,
        "joinProofOk": join_ok,
    }
    if join_ok and recon_pct >= 70:
        executive["20_f04_api_ou_parser"] = "API estruturada para transacional; parser/UI para nominal"
        parecer = "[PARECER FINAL: PRESTACAO CONTAS/PARSER NECESSÁRIO PARA F04]"
    elif join_ok:
        executive["20_f04_api_ou_parser"] = "API parcial + parser prestação"
        parecer = "[PARECER FINAL: PRESTACAO CONTAS/PARSER NECESSÁRIO PARA F04]"
    else:
        executive["20_f04_api_ou_parser"] = "Join insuficiente"
        parecer = "[PARECER FINAL: RETIDO — JOIN VENDA/CAIXA/FORMA PAGAMENTO NÃO COMPROVADO]"

    out = {
        "sprint": "D01",
        "windows": results,
        "executiveAnswers": executive,
        "parecerFinal": parecer,
        "qa": {
            "joinMatrixFilled": bool(joins),
            "joinProofOk": join_ok,
            "reconstructionMeasured": recon_pct is not None,
        },
    }
    dest = ROOT / "scripts" / "d01_operational_join_probe.json"
    # strip rows for JSON size
    slim = json.loads(json.dumps(out, default=str))
    for w in slim.get("windows", {}).values():
        perf = w.get("performance") or {}
        for ep in perf.values():
            ep.pop("rows", None)
    dest.write_text(json.dumps(slim, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {dest}")
    print(parecer)


if __name__ == "__main__":
    asyncio.run(main())
