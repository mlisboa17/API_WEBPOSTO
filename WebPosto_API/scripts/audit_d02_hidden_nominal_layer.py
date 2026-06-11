#!/usr/bin/env python3
"""D02 — Hidden Nominal Layer Discovery (READ ONLY)."""
from __future__ import annotations

import asyncio
import json
import os
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
TARGET_EMPRESA = 5555
CRITICAL_OPERATORS = [276288, 294273, 213391]

OPERATIONAL_ENDPOINTS: list[tuple[str, str | None]] = [
    ("caixa_rede", "caixa"),
    ("caixa_apresentado_rede", "caixa_apresentado"),
    ("venda", None),
    ("venda_item", None),
    ("venda_forma_pagamento_rede", "venda_forma_pagamento"),
    ("abastecimento", None),
    ("nfce", None),
    ("movimento_conta", None),
    ("transferencia_bancaria", None),
]

NOMINAL_ENDPOINTS: dict[str, str] = {
    "FuncionarioRede": "/INTEGRACAO/FUNCIONARIO_REDE",
    "ConsultarFuncionario": "/INTEGRACAO/CONSULTAR_FUNCIONARIO",
    "Funcionario": "/INTEGRACAO/FUNCIONARIO",
    "FuncionarioEmpresa": "/INTEGRACAO/FUNCIONARIO_EMPRESA",
    "FuncionarioMovimento": "/INTEGRACAO/FUNCIONARIO_MOVIMENTO",
    "ValeFuncionarioRede": "/INTEGRACAO/VALE_FUNCIONARIO_REDE",
    "Usuario": "/INTEGRACAO/USUARIO",
    "UsuarioEmpresaRede": "/INTEGRACAO/USUARIO_EMPRESA_REDE",
    "GrupoMeta": "/INTEGRACAO/GRUPO_META",
    "ProdutoMeta": "/INTEGRACAO/PRODUTO_META",
    "FechamentoCaixa": "/INTEGRACAO/FECHAMENTO_CAIXA",
}

NOMINAL_KEYWORDS = re.compile(
    r"(nome|funcionario|operador|usuario|colaborador|cpf|matricula|apelido|meta|objetivo|alvo|target|quota|"
    r"produtiv|performance|score|ranking|resultado|fundo|abertura|suprimento)",
    re.I,
)

LOGOS_USED_FIELDS = {
    "empresaCodigo", "caixaCodigo", "vendaCodigo", "vendaItemCodigo", "funcionarioCodigo", "pdvCodigo",
    "turnoCodigo", "turno", "dataMovimento", "dataHora", "dataEmissao", "dataFiscal", "valorPagamento",
    "nomeFormaPagamento", "formaPagamentoCodigo", "administradoraCodigo", "totalVenda", "totalDesconto",
    "quantidade", "cancelada", "troco", "bicoCodigo", "tanqueCodigo", "produtoCodigo", "produtoLmcCodigo",
    "abastecimentoCodigo", "codigoFrentista", "codigoBico", "valorTotal", "encerrante", "nfceCodigo",
    "situacao", "numeroDocumento", "serieDocumento", "diferenca", "apurado", "fechamento", "fechado",
    "consolidado", "dinheiroApresentado", "dinheiroApurado", "cartaoApresentado", "despesaApresentado",
    "historico", "valor", "tipo", "contaCodigo", "planoContaCodigo",
}

EXCLUSIVE_PRESTACAO = [
    "funcionarioNome",
    "participacaoIndividual (oficial UI)",
    "produtividadeFuncionario (oficial UI)",
    "metaFuncionario",
    "fundoCaixa (rótulo Prestação)",
    "layout operacional turno",
]


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


def field_stats(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    total = len(rows)
    non_null = sum(1 for r in rows if r.get(field) not in (None, "", "0", 0))
    samples = []
    for r in rows:
        v = r.get(field)
        if v not in (None, "", "0", 0):
            samples.append(v)
            if len(samples) >= 5:
                break
    return {
        "exists": non_null > 0,
        "coveragePct": round(100 * non_null / total, 2) if total else 0.0,
        "samples": samples[:5],
    }


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
            resp = await asyncio.wait_for(client.call_endpoint(key, params=page_params), timeout=120.0)
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

    return {
        "key": key,
        "status": status,
        "error": error,
        "timeout": timeout,
        "truncated": not ultima and pages >= max_pages,
        "pages": pages,
        "count": len(all_rows),
        "elapsedSec": round(time.perf_counter() - t0, 2),
        "rows": all_rows,
    }


async def fetch_funcionario_catalog(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    di: str,
    df: str,
    max_pages: int = 10,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    path = "/INTEGRACAO/FUNCIONARIO"
    for page in range(max_pages):
        params: dict[str, Any] = {"CHAVE": api_key, "dataInicial": di, "dataFinal": df}
        if page:
            params["pagina"] = page + 1
        try:
            resp = await asyncio.wait_for(client.get(path, params=params), timeout=45.0)
        except asyncio.TimeoutError:
            break
        if resp.status_code != 200:
            break
        chunk = _rows(resp.json())
        if not chunk:
            break
        rows.extend(chunk)
        payload = resp.json()
        if isinstance(payload, dict) and payload.get("ultimaPagina", True):
            break
    return rows


def funcionario_index(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    idx: dict[int, dict[str, Any]] = {}
    for r in rows:
        try:
            idx[int(r.get("funcionarioCodigo"))] = r
        except (TypeError, ValueError):
            pass
    return idx


async def probe_nominal_endpoint(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    name: str,
    path: str,
    di: str,
    df: str,
) -> dict[str, Any]:
    params = {"CHAVE": api_key, "dataInicial": di, "dataFinal": df}
    entry: dict[str, Any] = {
        "endpoint": name,
        "path": path,
        "httpStatus": 0,
        "registros": 0,
        "campos": [],
        "nomeFields": [],
        "keywordFields": [],
        "samples": [],
        "timeout": False,
        "error": None,
    }
    try:
        resp = await asyncio.wait_for(client.get(path, params=params), timeout=45.0)
        entry["httpStatus"] = resp.status_code
        if resp.status_code != 200:
            return entry
        payload = resp.json()
        rows = _rows(payload)
        entry["registros"] = len(rows)
        if rows:
            keys = sorted(rows[0].keys())
            entry["campos"] = keys
            entry["nomeFields"] = [k for k in keys if re.search(r"nome|funcionario|operador|usuario|cpf|matricula|apelido", k, re.I)]
            entry["keywordFields"] = [k for k in keys if NOMINAL_KEYWORDS.search(k)]
            entry["samples"] = rows[:2]
    except asyncio.TimeoutError:
        entry["timeout"] = True
        entry["error"] = "timeout"
    except Exception as exc:
        entry["error"] = str(exc)[:200]
    return entry


def scan_hidden_fields(sources: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    by_source: dict[str, Any] = {}
    strategic: list[dict[str, Any]] = []
    all_unknown: Counter[str] = Counter()

    for source, rows in sources.items():
        if not rows:
            by_source[source] = {"totalRows": 0, "allKeys": [], "unusedInLogos": [], "emptyFields": [], "unknownStrategic": []}
            continue
        keys = sorted({k for r in rows for k in r.keys()})
        unused = []
        empty = []
        unknown_strategic = []
        for k in keys:
            non_null = sum(1 for r in rows if r.get(k) not in (None, "", "0", 0))
            pct = round(100 * non_null / len(rows), 2)
            if k not in LOGOS_USED_FIELDS:
                unused.append({"field": k, "coveragePct": pct})
                all_unknown[k] += non_null
            if pct == 0:
                empty.append(k)
            if k not in LOGOS_USED_FIELDS and pct >= 5 and NOMINAL_KEYWORDS.search(k):
                unknown_strategic.append({"field": k, "coveragePct": pct, "source": source})
                strategic.append({"field": k, "coveragePct": pct, "source": source})
        by_source[source] = {
            "totalRows": len(rows),
            "allKeys": keys,
            "unusedInLogos": sorted(unused, key=lambda x: -x["coveragePct"])[:30],
            "emptyFields": empty[:40],
            "unknownStrategic": unknown_strategic,
        }

    top_strategic = sorted(strategic, key=lambda x: -x["coveragePct"])[:25]
    return {"bySource": by_source, "topStrategic": top_strategic, "globalUnusedHits": dict(all_unknown.most_common(30))}


def trace_operators(
    operators: list[int],
    venda: list[dict],
    caixa: list[dict],
    abast: list[dict],
    venda_item: list[dict],
    funcionario_idx: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    caixa_by_func: dict[int, list[dict]] = defaultdict(list)
    for c in caixa:
        fc = c.get("funcionarioCodigo")
        if fc is not None:
            caixa_by_func[int(fc)].append(c)

    traces: dict[str, Any] = {}
    for op in operators:
        op_vendas = [r for r in venda if int(r.get("funcionarioCodigo") or 0) == op]
        op_caixa = caixa_by_func.get(op, [])
        op_abast = [r for r in abast if int(r.get("codigoFrentista") or 0) == op]
        op_items = [r for r in venda_item if int(r.get("funcionarioCodigo") or 0) == op]

        empresas = sorted({int(r.get("empresaCodigo") or 0) for r in op_vendas + op_caixa if r.get("empresaCodigo")})
        pdvs = sorted({int(c.get("pdvCodigo") or 0) for c in op_caixa if c.get("pdvCodigo")})
        turnos = sorted({str(c.get("turnoCodigo") or c.get("turno") or "") for c in op_caixa if c.get("turnoCodigo") or c.get("turno")})

        nome_hits = []
        for rows in (op_vendas, op_caixa, op_abast, op_items):
            for r in rows:
                for k, v in r.items():
                    if re.search(r"nome|cpf|matricula|apelido", k, re.I) and v not in (None, "", 0):
                        nome_hits.append({k: v})

        cadastro = (funcionario_idx or {}).get(op) or {}
        cadastro_nome = cadastro.get("nome")
        if cadastro_nome:
            nome_hits.append({"funcionario.nome": cadastro_nome})
        if cadastro.get("cpf"):
            nome_hits.append({"funcionario.cpf": cadastro.get("cpf")})
        if cadastro.get("funcionarioReferencia"):
            nome_hits.append({"funcionario.referencia": cadastro.get("funcionarioReferencia")})

        nominalizavel = bool(cadastro_nome) or any(
            "nome" in str(k).lower() for hit in nome_hits for k in hit.keys()
        )

        traces[str(op)] = {
            "funcionarioCodigo": op,
            "vendasCount": len(op_vendas),
            "caixaTurnosCount": len(op_caixa),
            "abastecimentosCount": len(op_abast),
            "vendaItensCount": len(op_items),
            "empresas": empresas,
            "pdvs": pdvs,
            "turnos": turnos,
            "volumeVendas": round(sum(float(_dec(r.get("totalVenda"))) for r in op_vendas), 2),
            "cadastroFuncionario": {
                "encontrado": bool(cadastro),
                "nome": cadastro_nome,
                "cpf": cadastro.get("cpf"),
                "referencia": cadastro.get("funcionarioReferencia"),
                "ativo": cadastro.get("ativo"),
                "empresaCodigo": cadastro.get("empresaCodigo"),
            },
            "nomeFieldsFound": nome_hits[:10],
            "nominalizavel": nominalizavel,
            "identidadeReal": "funcionario_api" if cadastro_nome else ("codigo_only" if not nominalizavel else "transacional_parcial"),
        }
    return traces


def participation_analysis(venda: list[dict], caixa: list[dict]) -> dict[str, Any]:
    caixa_idx = {(c.get("empresaCodigo"), c.get("caixaCodigo")): c for c in caixa}
    by_func: Counter[str] = Counter()
    total = Decimal("0")
    for r in venda:
        if str(r.get("cancelada") or "").lower() in {"1", "true", "s", "sim", "cancelada"}:
            continue
        val = _dec(r.get("totalVenda"))
        total += val
        by_func[str(r.get("funcionarioCodigo"))] += float(val)

    participacao = {
        k: round(100 * v / float(total), 2) if total else 0.0 for k, v in by_func.items()
    }
    official_field = any(
        k for r in venda for k in r.keys()
        if re.search(r"participacao|participação|percentualFuncionario", k, re.I)
    )
    ranking_field = any(k for r in venda for k in r.keys() if re.search(r"ranking|score|produtiv", k, re.I))

    return {
        "calculavel": len(participacao) > 0,
        "campoOficial": official_field,
        "rankingInterno": ranking_field,
        "participacaoCalculada": participacao,
        "operadoresNoTurno": len(participacao),
        "origem": "calculado_VENDA.totalVenda" if participacao else "indisponivel",
    }


def productivity_analysis(venda: list[dict], abast: list[dict], venda_item: list[dict]) -> dict[str, Any]:
    keywords_found: Counter[str] = Counter()
    for source, rows in (("VENDA", venda), ("ABASTECIMENTO", abast), ("VENDA_ITEM", venda_item)):
        for r in rows:
            for k in r.keys():
                if re.search(r"produtiv|meta|performance|score|ranking|resultado", k, re.I):
                    keywords_found[f"{source}.{k}"] += 1

    by_frentista = Counter(str(r.get("codigoFrentista")) for r in abast if r.get("codigoFrentista"))
    by_func_venda = Counter(str(r.get("funcionarioCodigo")) for r in venda if r.get("funcionarioCodigo"))

    return {
        "campoOficialPronto": len(keywords_found) > 0,
        "keywordsEncontrados": dict(keywords_found),
        "classificacao": "B_calculada" if not keywords_found else "A_pronta",
        "proxyAbastecimentos": dict(by_frentista.most_common(15)),
        "proxyVendas": dict(by_func_venda.most_common(15)),
        "origemPrestacao": "UI_calculada_ou_regra_interna_WebPosto",
    }


def fundo_caixa_forensics(
    caixa: list[dict],
    caixa_ap: list[dict],
    movimento: list[dict],
    transferencia: list[dict],
) -> dict[str, Any]:
    abertura_stats = field_stats(caixa, "abertura")
    fundo_named = any(re.search(r"fundo", k, re.I) for r in caixa for k in r.keys())
    suprimento_rows = [
        r for r in movimento
        if re.search(r"supr|fundo|abertura|refor", str(r.get("historico") or ""), re.I)
    ]
    saldo_inicial_rows = [
        r for r in movimento
        if re.search(r"saldo.?inicial|abertura", str(r.get("historico") or ""), re.I)
    ]

    abertura_samples = [
        {
            "empresaCodigo": r.get("empresaCodigo"),
            "caixaCodigo": r.get("caixaCodigo"),
            "turnoCodigo": r.get("turnoCodigo"),
            "pdvCodigo": r.get("pdvCodigo"),
            "funcionarioCodigo": r.get("funcionarioCodigo"),
            "abertura": r.get("abertura"),
        }
        for r in caixa
        if r.get("abertura") not in (None, "", 0)
    ][:8]

    reconstruivel = abertura_stats["exists"] or len(suprimento_rows) > 0
    return {
        "campoFundoCaixa": fundo_named,
        "campoAbertura": abertura_stats,
        "suprimentoInicial": {"count": len(suprimento_rows), "exists": len(suprimento_rows) > 0},
        "saldoInicial": {"count": len(saldo_inicial_rows), "exists": len(saldo_inicial_rows) > 0},
        "caixaApresentadoCount": len(caixa_ap),
        "transferenciaCount": len(transferencia),
        "aberturaSamples": abertura_samples,
        "reconstruivel": reconstruivel,
        "origemProvavel": "CAIXA.abertura (+ MOVIMENTO_CONTA inferido)" if reconstruivel else "apenas_prestacao",
        "gapVsPrestacao": "rótulo fundoCaixa ≠ abertura numérica sem regra UI",
    }


def goal_discovery(all_rows: dict[str, list[dict]]) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    for source, rows in all_rows.items():
        for r in rows:
            for k, v in r.items():
                if re.search(r"^meta|objetivo|alvo|target|quota", k, re.I) and v not in (None, "", 0):
                    hits.append({"source": source, "field": k, "sample": v})
                    if len(hits) >= 40:
                        break
            if len(hits) >= 40:
                break
    by_entity = {
        "funcionario": any(re.search(r"funcionario|operador|frentista", h["field"], re.I) for h in hits),
        "pdv": any(re.search(r"pdv", h["field"], re.I) for h in hits),
        "turno": any(re.search(r"turno", h["field"], re.I) for h in hits),
        "empresa": any(re.search(r"empresa", h["field"], re.I) for h in hits),
    }
    return {"hits": hits[:25], "byEntity": by_entity, "metaOperacionalApi": len(hits) > 0}


def employee_nominal_discovery(
    nominal_probes: list[dict],
    transactional_rows: dict[str, list[dict]],
) -> dict[str, Any]:
    nome_in_api = False
    cpf_in_api = False
    matricula_in_api = False
    apelido_in_api = False
    status_ativo = False
    nome_completo = False

    for probe in nominal_probes:
        if probe.get("httpStatus") != 200 or not probe.get("registros"):
            continue
        for k in probe.get("campos") or []:
            kl = k.lower()
            if "nome" in kl:
                nome_in_api = True
                if "completo" in kl or kl in {"nome", "nomefuncionario", "nomefunc"}:
                    nome_completo = True
            if "cpf" in kl:
                cpf_in_api = True
            if "matricula" in kl or "matric" in kl:
                matricula_in_api = True
            if "apelido" in kl or "operador" in kl:
                apelido_in_api = True
            if "ativo" in kl or "status" in kl or "situacao" in kl:
                status_ativo = True

    for source, rows in transactional_rows.items():
        for r in rows[:500]:
            for k, v in r.items():
                if v in (None, "", 0):
                    continue
                kl = k.lower()
                if kl == "funcionarionome" or kl == "nomefuncionario":
                    nome_in_api = True
                    nome_completo = True
                if "cpf" in kl:
                    cpf_in_api = True
                if "matricula" in kl:
                    matricula_in_api = True
                if "apelido" in kl:
                    apelido_in_api = True

    funcionario_nome_field = any(
        r.get("funcionarioNome") or r.get("nomeFuncionario")
        for rows in transactional_rows.values()
        for r in rows
    )

    return {
        "1_funcionarioNome": funcionario_nome_field or nome_in_api,
        "2_nomeCompleto": nome_completo,
        "3_cpf": cpf_in_api,
        "4_matricula": matricula_in_api,
        "5_apelidoOperacional": apelido_in_api,
        "6_statusAtivo": status_ativo,
        "endpointsAuditados": [p["path"] for p in nominal_probes],
        "endpointsComDados": [
            p["path"] for p in nominal_probes if p.get("httpStatus") == 200 and p.get("registros", 0) > 0
        ],
        "endpoints401": [p["path"] for p in nominal_probes if p.get("httpStatus") in {401, 403}],
        "conclusao": "Somente funcionarioCodigo/codigoFrentista nos endpoints transacionais autorizados",
    }


def gap_analysis(
    employee: dict,
    participation: dict,
    productivity: dict,
    fundo: dict,
    goal: dict,
    critical_trace: dict[str, Any],
) -> dict[str, Any]:
    funcionario_api = bool(employee.get("1_funcionarioNome"))
    critical_ok = all(
        (critical_trace.get(str(op)) or {}).get("nominalizavel") for op in CRITICAL_OPERATORS
    )
    fields = {
        "funcionarioNome": {
            "origem": "/INTEGRACAO/FUNCIONARIO.nome" if funcionario_api else "prestacao_ui",
            "api": funcionario_api,
            "calculavel": False,
            "inferivel": funcionario_api and not critical_ok,
        },
        "participacaoIndividual": {
            "origem": "calculavel_venda",
            "api": False,
            "calculavel": participation.get("calculavel"),
            "inferivel": True,
        },
        "produtividadeFuncionario": {
            "origem": "proxy_venda_abastecimento",
            "api": productivity.get("classificacao") == "A_pronta",
            "calculavel": True,
            "inferivel": True,
        },
        "metaFuncionario": {
            "origem": "grupo_meta_isolado",
            "api": goal.get("metaOperacionalApi"),
            "calculavel": False,
            "inferivel": False,
        },
        "fundoCaixa": {
            "origem": "caixa_abertura_parcial",
            "api": fundo.get("campoAbertura", {}).get("exists"),
            "calculavel": fundo.get("reconstruivel"),
            "inferivel": True,
        },
        "layoutOperacionalTurno": {
            "origem": "prestacao_pdf",
            "api": False,
            "calculavel": False,
            "inferivel": False,
        },
    }
    exclusivo = [k for k, v in fields.items() if not v["api"] and not v["calculavel"]]
    calculavel = [k for k, v in fields.items() if v["calculavel"]]
    inferivel = [k for k, v in fields.items() if v["inferivel"]]
    inexistente = [k for k, v in fields.items() if not v["api"] and not v["calculavel"] and not v["inferivel"]]

    d01_cov = 87.5
    bonus = 0.0
    if participation.get("calculavel"):
        bonus += 2.5
    if productivity.get("classificacao") == "B_calculada" or productivity.get("calculavel"):
        bonus += 2.5
    if fundo.get("reconstruivel"):
        bonus += 2.5
    if funcionario_api:
        bonus += 2.5
    nova_cov = min(100.0, round(d01_cov + bonus, 2))

    return {
        "fields": fields,
        "exclusivoPrestacao": exclusivo,
        "calculavel": calculavel,
        "inferivel": inferivel,
        "inexistenteApi": inexistente,
        "coberturaD01Pct": d01_cov,
        "coberturaD02Pct": nova_cov,
        "atinge95": nova_cov >= 95,
        "atinge100": len(exclusivo) == 0,
    }


def f04_impact(gap: dict, critical_trace: dict[str, Any]) -> dict[str, Any]:
    impact = {
        "funcionarioNome": "OBRIGATÓRIO",
        "participacaoIndividual": "IMPORTANTE",
        "produtividadeFuncionario": "IMPORTANTE",
        "metaFuncionario": "OPCIONAL",
        "fundoCaixa": "IMPORTANTE",
        "layoutOperacionalTurno": "OPCIONAL",
    }
    critical_ok = all((critical_trace.get(str(op)) or {}).get("nominalizavel") for op in CRITICAL_OPERATORS)
    funcionario_api = "funcionarioNome" not in (gap.get("inexistenteApi") or [])
    depende_pdf = not (funcionario_api and critical_ok)
    return {"classificacao": impact, "f04DependePdf": depende_pdf, "operadoresCriticosNominalizados": critical_ok}


def architecture_decision(gap: dict, employee: dict, critical_trace: dict[str, Any]) -> dict[str, Any]:
    funcionario_api = bool(employee.get("1_funcionarioNome"))
    critical_ok = all((critical_trace.get(str(op)) or {}).get("nominalizavel") for op in CRITICAL_OPERATORS)
    exclusivos_hard = gap.get("exclusivoPrestacao") or []
    only_layout_meta = set(exclusivos_hard).issubset({"metaFuncionario", "layoutOperacionalTurno"})

    if funcionario_api and critical_ok and only_layout_meta and gap.get("coberturaD02Pct", 0) >= 95:
        opcao = "A"
        parecer = "[PARECER FINAL: API SUFICIENTE PARA F04]"
    elif funcionario_api or gap.get("coberturaD02Pct", 0) >= 90:
        opcao = "B"
        parecer = "[PARECER FINAL: MODELO HÍBRIDO NECESSÁRIO]"
    else:
        opcao = "C"
        parecer = "[PARECER FINAL: PARSER DA PRESTAÇÃO OBRIGATÓRIO]"

    return {
        "opcao": opcao,
        "descricao": {
            "A": "API sozinha é suficiente",
            "B": "API + Prestação (parser/UI nominal)",
            "C": "Parser Prestação obrigatório",
        }[opcao],
        "parecerFinal": parecer,
    }


async def probe_window(
    client: WebPostoClient,
    nominal_client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    label: str,
    di: str,
    df: str,
    max_pages: int,
    nominal_cache: list[dict] | None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    fetched: dict[str, dict[str, Any]] = {}
    for primary, fallback in OPERATIONAL_ENDPOINTS:
        result = await fetch_endpoint(client, primary, di, df, max_pages)
        if not result["count"] and fallback:
            fb = await fetch_endpoint(client, fallback, di, df, max_pages)
            if fb["count"] or fb["status"] == 200:
                fb["usedFallback"] = primary
                result = fb
        store_key = primary.split("_rede")[0] if "_rede" in primary else primary
        fetched[store_key] = result

    def rows(k: str) -> list[dict]:
        return fetched.get(k, {}).get("rows") or []

    caixa = rows("caixa")
    venda = rows("venda")
    abast = rows("abastecimento")
    vi = rows("venda_item")
    cap = rows("caixa_apresentado")
    mov = rows("movimento_conta")
    tr = rows("transferencia_bancaria")

    def filtrar(rs: list[dict], emp: int) -> list[dict]:
        return [r for r in rs if int(r.get("empresaCodigo") or 0) == emp]

    sources_emp = {
        "VENDA": filtrar(venda, TARGET_EMPRESA),
        "VENDA_ITEM": filtrar(vi, TARGET_EMPRESA),
        "ABASTECIMENTO": filtrar(abast, TARGET_EMPRESA),
        "CAIXA": filtrar(caixa, TARGET_EMPRESA),
        "CAIXA_APRESENTADO": filtrar(cap, TARGET_EMPRESA),
        "NFCE": filtrar(rows("nfce"), TARGET_EMPRESA),
        "VENDA_FORMA_PAGAMENTO": filtrar(rows("venda_forma_pagamento"), TARGET_EMPRESA),
    }

    nominal_probes = nominal_cache
    funcionario_catalog: list[dict[str, Any]] = []
    if nominal_probes is None:
        nominal_probes = []
        for name, path in NOMINAL_ENDPOINTS.items():
            nominal_probes.append(
                await probe_nominal_endpoint(nominal_client, base_url, api_key, name, path, di, df)
            )
        funcionario_catalog = await fetch_funcionario_catalog(nominal_client, base_url, api_key, di, df)
    else:
        funcionario_catalog = await fetch_funcionario_catalog(nominal_client, base_url, api_key, di, df)

    func_idx = funcionario_index(funcionario_catalog)

    employee = employee_nominal_discovery(nominal_probes, sources_emp)
    if funcionario_catalog:
        employee["funcionarioCatalogCount"] = len(funcionario_catalog)
        employee["conclusao"] = (
            "/INTEGRACAO/FUNCIONARIO expõe nome/cpf/ativo — join por funcionarioCodigo; "
            "transacional permanece codigo-only"
        )

    operators = trace_operators(CRITICAL_OPERATORS, venda, caixa, abast, vi, func_idx)
    participation = participation_analysis(sources_emp["VENDA"], sources_emp["CAIXA"])
    productivity = productivity_analysis(sources_emp["VENDA"], sources_emp["ABASTECIMENTO"], sources_emp["VENDA_ITEM"])
    fundo = fundo_caixa_forensics(sources_emp["CAIXA"], sources_emp["CAIXA_APRESENTADO"], mov, tr)
    goal = goal_discovery(sources_emp)
    hidden = scan_hidden_fields(sources_emp)
    gap = gap_analysis(employee, participation, productivity, fundo, goal, operators)
    f04 = f04_impact(gap, operators)
    arch = architecture_decision(gap, employee, operators)

    performance = {k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in fetched.items()}

    return {
        "window": label,
        "periodo": {"inicio": di, "fim": df},
        "elapsedSec": round(time.perf_counter() - t0, 2),
        "performance": performance,
        "employeeNominalDiscovery": employee,
        "nominalEndpointProbes": nominal_probes,
        "operatorIdentityTrace": operators,
        "funcionarioCatalogCount": len(funcionario_catalog),
        "participationDiscovery": participation,
        "productivityDiscovery": productivity,
        "fundoCaixaForensics": fundo,
        "goalDiscovery": goal,
        "hiddenFieldScan": hidden,
        "prestacaoGapAnalysis": gap,
        "f04ImpactAnalysis": f04,
        "architectureDecision": arch,
        "counts": {k: len(v) for k, v in sources_emp.items()},
    }


async def main() -> None:
    only = os.environ.get("D02_WINDOW")
    windows = {only: WINDOWS[only]} if only and only in WINDOWS else WINDOWS
    max_pages = int(os.environ.get("D02_MAX_PAGES", "12"))

    cfg = load_core_config()
    client = WebPostoClient(cfg)
    d01_path = ROOT / "scripts" / "d01_operational_join_probe.json"
    d01 = json.loads(d01_path.read_text(encoding="utf-8")) if d01_path.exists() else {}

    out_path = ROOT / "scripts" / "d02_hidden_nominal_layer.json"
    existing: dict[str, Any] = {}
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    results: dict[str, Any] = dict(existing.get("windows") or {})
    nominal_cache: list[dict] | None = None
    if results:
        first = results.get("7d") or results.get("30d") or next(iter(results.values()), {})
        nominal_cache = first.get("nominalEndpointProbes")

    async with httpx.AsyncClient(base_url=cfg.webposto_base_url, timeout=45.0) as nominal_client:
        for label, (di, df) in windows.items():
            if label in results and not results[label].get("error") and os.environ.get("D02_FORCE") != "1":
                print(f"D02 skip {label} (already in json, set D02_FORCE=1 to redo)")
                continue
            print(f"D02 probe {label} {di}..{df} max_pages={max_pages}", flush=True)
            try:
                win = await probe_window(
                    client, nominal_client, cfg.webposto_base_url, cfg.webposto_api_key,
                    label, di, df, max_pages, nominal_cache,
                )
                if nominal_cache is None:
                    nominal_cache = win.get("nominalEndpointProbes")
                results[label] = win
            except Exception as exc:
                results[label] = {"window": label, "error": str(exc)[:400]}
            elapsed = results[label].get("elapsedSec", "?")
            print(f"  done {label} elapsed={elapsed}s", flush=True)

            # save incremental
            partial = {
                "sprint": "D02",
                "module": "Hidden Nominal Layer Discovery",
                "windows": results,
                "partial": True,
            }
            out_path.write_text(json.dumps(partial, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    ref = results.get("7d") or results.get("30d") or next(iter(results.values()), {})
    emp = ref.get("employeeNominalDiscovery") or {}
    part = ref.get("participationDiscovery") or {}
    prod = ref.get("productivityDiscovery") or {}
    fundo = ref.get("fundoCaixaForensics") or {}
    goal = ref.get("goalDiscovery") or {}
    gap = ref.get("prestacaoGapAnalysis") or {}
    arch = ref.get("architectureDecision") or {}
    ops = ref.get("operatorIdentityTrace") or {}

    d01_exec = d01.get("executiveAnswers") or {}
    d01_recon = d01_exec.get("19_cobertura_reconstrucao_pct", 87.5)

    executive = {
        "1_funcionarioNomeEndpoint": emp.get("1_funcionarioNome"),
        "2_cpfOperador": emp.get("3_cpf"),
        "3_matricula": emp.get("4_matricula"),
        "4_produtividadeOficial": prod.get("classificacao") == "A_pronta",
        "5_participacaoOficial": part.get("campoOficial"),
        "6_fundoCaixa": fundo.get("campoFundoCaixa") or fundo.get("campoAbertura", {}).get("exists"),
        "7_metaOperacional": goal.get("metaOperacionalApi"),
        "8_rankingOficial": part.get("rankingInterno"),
        "9_operadoresNominalizaveis": {
            str(op): (ops.get(str(op)) or {}).get("nominalizavel", False) for op in CRITICAL_OPERATORS
        },
        "10_camposExclusivosSemOrigem": len(gap.get("exclusivoPrestacao") or []),
        "11_calculaveis": len(gap.get("calculavel") or []),
        "12_inferiveis": len(gap.get("inferivel") or []),
        "13_inexistentesApi": len(gap.get("inexistenteApi") or []),
        "14_pdfNecessario": arch.get("opcao") != "A",
        "15_novaCoberturaPct": gap.get("coberturaD02Pct"),
        "16_atinge95": gap.get("atinge95"),
        "17_atinge100": gap.get("atinge100"),
        "18_campoMaisValiosoOculto": "funcionarioNome",
        "19_f04DependePdf": (ref.get("f04ImpactAnalysis") or {}).get("f04DependePdf"),
        "20_arquiteturaDefinitiva": arch.get("opcao"),
        "coberturaD01Pct": d01_recon,
    }

    out = {
        "sprint": "D02",
        "module": "Hidden Nominal Layer Discovery",
        "windows": results,
        "executiveAnswers": executive,
        "exclusivePrestacaoInvestigated": EXCLUSIVE_PRESTACAO,
        "parecerFinal": arch.get("parecerFinal", "[PARECER FINAL: MODELO HÍBRIDO NECESSÁRIO]"),
        "d01BaselineLoaded": d01_path.exists(),
    }

    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out_path}", flush=True)
    print(arch.get("parecerFinal", ""), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
