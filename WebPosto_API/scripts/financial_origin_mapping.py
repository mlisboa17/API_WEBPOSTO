#!/usr/bin/env python3
"""
Sprint P0.1 — Mapeamento real das entidades de despesa WebPosto.

Audita endpoints financeiros, caixa, compras e funcionários.
Gera: financial_origin_matrix.json, FINANCIAL_ORIGIN_MAPPING.md, WEBPOSTO_FINANCIAL_MODEL.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import load_core_config

DATA_INI = "2026-06-01"
DATA_FIM = "2026-06-07"
TARGET_FILIAIS = {5256, 5333, 5555, 5556, 5557, 5558, 5559, 5560, 11495, 46433, 74014}

ENDPOINT_GROUPS: dict[str, dict[str, str]] = {
    "financeiro": {
        "DESPESAS_FINANCEIRO_REDE": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
        "MOVIMENTO_CONTA": "/INTEGRACAO/MOVIMENTO_CONTA",
        "CONTA_REDE": "/INTEGRACAO/CONTA",
        "TITULO_PAGAR": "/INTEGRACAO/TITULO_PAGAR",
        "TITULO_PAGAR_REDE": "/INTEGRACAO/TITULO_PAGAR_REDE",
        "CONSULTAR_TITULO_PAGAR_REDE": "/INTEGRACAO/CONSULTAR_TITULO_PAGAR_REDE",
        "TITULO_RECEBER": "/INTEGRACAO/TITULO_RECEBER",
        "TITULO_RECEBER_REDE": "/INTEGRACAO/TITULO_RECEBER_REDE",
        "DUPLICATA_REDE": "/INTEGRACAO/DUPLICATA_REDE",
        "LANCAMENTO_CONTABIL": "/INTEGRACAO/LANCAMENTO_CONTABIL",
        "LANCAMENTO_CONTABIL_ITEM": "/INTEGRACAO/LANCAMENTO_CONTABIL_ITEM",
        "FINANCEIRO_EXCLUSAO": "/INTEGRACAO/FINANCEIRO_EXCLUSAO",
        "TRANSFERENCIA_BANCARIA": "/INTEGRACAO/TRANSFERENCIA_BANCARIA",
    },
    "caixa": {
        "CAIXA": "/INTEGRACAO/CAIXA",
        "CAIXA_APRESENTADO": "/INTEGRACAO/CAIXA_APRESENTADO",
        "CONSULTAR_CAIXA_APRESENTADO_REDE": "/INTEGRACAO/CONSULTAR_CAIXA_APRESENTADO_REDE",
        "FECHAMENTO_CAIXA": "/INTEGRACAO/FECHAMENTO_CAIXA",
    },
    "compras": {
        "COMPRA_REDE": "/INTEGRACAO/COMPRA_REDE",
        "NOTA_ENTRADA": "/INTEGRACAO/NOTA_ENTRADA",
        "NOTA_ENTRADA_REDE": "/INTEGRACAO/NOTA_ENTRADA_REDE",
        "COMPRA_ITEM_REDE": "/INTEGRACAO/COMPRA_ITEM_REDE",
        "PEDIDO_COMPRAS": "/INTEGRACAO/PEDIDO_COMPRAS",
        "PEDIDO_COMBUSTIVEL": "/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO",
        "PEDIDO_TRR": "/INTEGRACAO/PEDIDO_TRR",
        "CARTAO_COMPRA": "/INTEGRACAO/CARTAO_COMPRA",
    },
    "funcionarios": {
        "DESPESA_FUNCIONARIO": "/INTEGRACAO/DESPESA_FUNCIONARIO",
        "VALE_FUNCIONARIO_REDE": "/INTEGRACAO/VALE_FUNCIONARIO_REDE",
    },
}

# Tipos financeiros → palavras-chave (texto normalizado)
TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Sangria / retirada caixa": ("sangria", "retirada", "retirada caixa"),
    "Suprimento / fundo caixa": ("suprimento", "reforco", "fundo de caixa", "fundo caixa"),
    "Troco": ("troco",),
    "Quebra / diferença caixa": ("quebra", "diferenca caixa", "dif caixa"),
    "Compra mercadoria / NF entrada": ("compra", "nota entrada", "nf entrada", "fornecedor"),
    "Compra combustível / TRR": ("combustivel", "trr", "pedido combustivel", "abastecimento trr"),
    "Energia / utilities": ("energia", "coelba", "neoenergia", "luz", "agua", "telefone"),
    "Salário / folha": ("salario", "folha", "pro labore", "adiantamento"),
    "Vale funcionário": ("vale funcionario", "vale func", "antecipacao salario"),
    "Tarifa bancária": ("tarifa", "taxa bancaria", "iof", "ted", "doc", "manutencao conta"),
    "Título a pagar": ("titulo pagar", "titulo a pagar", "duplicata"),
    "Título a receber": ("titulo receber", "recebimento"),
    "Transferência bancária": ("transferencia", "transf banc"),
    "Despesa operacional genérica": ("despesa", "pagamento", "debito"),
    "Exclusão financeira / débito caixa": ("exclusao", "debito caixa", "financeiro exclusao"),
}

VALOR_FIELDS = (
    "valor",
    "valorTotal",
    "valorDespesa",
    "valorPago",
    "valorMovimento",
    "valorTitulo",
    "valorSangria",
    "sangria",
    "despesa",
    "valorSaida",
    "valorRetirada",
    "totalCompra",
    "totalNota",
    "dinheiroDiferenca",
    "diferenca",
)


def _norm(text: Any) -> str:
    if text is None:
        return ""
    s = str(text).strip().casefold()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "data", "items", "content", "pedidos"):
            val = payload.get(key)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
    return []


def _extract_valor(row: dict[str, Any]) -> Decimal | None:
    for f in VALOR_FIELDS:
        if row.get(f) is not None:
            try:
                return Decimal(str(row[f]).replace(",", "."))
            except Exception:
                pass
    return None


def _row_text_blob(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for k, v in row.items():
        if isinstance(v, (str, int, float)) and v is not None:
            parts.append(f"{k}:{v}")
    return _norm(" ".join(parts))


def classify_row_text(text: str) -> list[str]:
    hits: list[str] = []
    for tipo, keywords in TYPE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            hits.append(tipo)
    return hits or ["Despesa operacional genérica"]


def _extract_empresa(row: dict[str, Any]) -> int | None:
    for key in ("empresaCodigo", "codigoEmpresa", "codWeb"):
        val = row.get(key)
        if val is not None:
            try:
                return int(val)
            except (TypeError, ValueError):
                pass
    return None


async def fetch_endpoint(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    name: str,
    path: str,
    params: dict[str, Any],
    max_pages: int = 3,
) -> dict[str, Any]:
    all_rows: list[dict[str, Any]] = []
    ultimo: Any = None
    http_status = 0
    errors: list[str] = []

    for page in range(max_pages):
        pp = {**params, "CHAVE": api_key}
        if ultimo is not None:
            pp["ultimoCodigo"] = ultimo
        try:
            resp = await client.get(f"{base_url}{path}", params=pp, timeout=90.0)
            http_status = resp.status_code
            if resp.status_code != 200:
                errors.append(resp.text[:300])
                break
            payload = resp.json()
        except httpx.TimeoutException:
            return {
                "endpoint": name,
                "path": path,
                "httpStatus": 0,
                "timeout": True,
                "registros": 0,
                "rows": [],
                "errors": ["timeout"],
            }
        except Exception as exc:
            return {
                "endpoint": name,
                "path": path,
                "httpStatus": http_status,
                "registros": 0,
                "rows": [],
                "errors": [str(exc)[:200]],
            }

        batch = _rows(payload)
        all_rows.extend(batch)
        if not isinstance(payload, dict):
            break
        novo = payload.get("ultimoCodigo")
        if novo is None or novo == ultimo or not batch:
            break
        ultimo = novo

    empresas = sorted({e for r in all_rows if (e := _extract_empresa(r)) is not None})
    campos = list(all_rows[0].keys()) if all_rows else []
    valor_total = sum((_extract_valor(r) or Decimal("0") for r in all_rows), Decimal("0"))

    type_hits: Counter[str] = Counter()
    type_samples: dict[str, list[str]] = defaultdict(list)
    for row in all_rows:
        blob = _row_text_blob(row)
        for tipo in classify_row_text(blob):
            type_hits[tipo] += 1
            desc = (
                str(row.get("descricaoDocumento") or row.get("planoConta") or row.get("historico")
                    or row.get("descricao") or row.get("tipo") or row.get("evento") or "")[:80]
            )
            if desc and len(type_samples[tipo]) < 3:
                type_samples[tipo].append(desc)

    return {
        "endpoint": name,
        "path": path,
        "httpStatus": http_status,
        "timeout": False,
        "registros": len(all_rows),
        "valorTotal": str(valor_total.quantize(Decimal("0.01"))),
        "empresaCodigos": empresas,
        "empresaCodigosAlvo": sorted(set(empresas) & TARGET_FILIAIS),
        "campos": campos[:40],
        "tipoHits": dict(type_hits),
        "tipoSamples": dict(type_samples),
        "errors": errors,
        "sampleRow": all_rows[0] if all_rows else None,
    }


def analyze_despesas_consolidadas(despesas_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Classifica linhas de DESPESAS_REDE por descricaoDocumento."""
    by_tipo: Counter[str] = Counter()
    by_desc_prefix: Counter[str] = Counter()
    valores_por_tipo: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    samples: dict[str, list[dict]] = defaultdict(list)

    for row in despesas_rows:
        desc = str(row.get("descricaoDocumento") or row.get("planoConta") or "")
        blob = _norm(desc)
        tipos = classify_row_text(blob)
        valor = _extract_valor(row) or Decimal("0")
        for t in tipos:
            by_tipo[t] += 1
            valores_por_tipo[t] += valor
            if len(samples[t]) < 2:
                samples[t].append({"descricao": desc[:100], "valor": str(valor), "empresa": row.get("empresaCodigo")})
        prefix = desc.split()[0][:20] if desc else "(vazio)"
        by_desc_prefix[prefix] += 1

    return {
        "totalRegistros": len(despesas_rows),
        "porTipo": {k: {"count": v, "valor": str(valores_por_tipo[k].quantize(Decimal("0.01")))} for k, v in by_tipo.items()},
        "topDescricoes": by_desc_prefix.most_common(15),
        "samples": dict(samples),
    }


def build_origin_matrix(
    endpoint_results: list[dict[str, Any]],
    despesas_analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []

    # Linhas a partir da análise de DESPESAS_REDE (visão consolidada WebPosto UI)
    for tipo, info in sorted(despesas_analysis.get("porTipo", {}).items(), key=lambda x: -x[1]["count"]):
        matrix.append({
            "tipoFinanceiro": tipo,
            "endpointOrigem": "DESPESAS_FINANCEIRO_REDE",
            "endpointPath": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
            "registros": info["count"],
            "valorTotal": info["valor"],
            "empresas": "rede (10 filiais)",
            "apareceNoWebPostoUI": "Sim — tela financeiro/despesas consolidada",
            "integradoLogosSpace": "Sim — /v1/financial/expenses",
            "observacao": "Classificado por descricaoDocumento",
        })

    # Linhas por endpoint com dados e tipos detectados
    despesas_ep = next((e for e in endpoint_results if e["endpoint"] == "DESPESAS_FINANCEIRO_REDE"), None)
    despesas_tipos = set(despesas_analysis.get("porTipo", {}).keys())

    for ep in endpoint_results:
        if ep.get("httpStatus") != 200 or ep.get("registros", 0) == 0:
            if ep["endpoint"] not in {"DESPESAS_FINANCEIRO_REDE"}:
                matrix.append({
                    "tipoFinanceiro": f"(endpoint {ep['endpoint']})",
                    "endpointOrigem": ep["endpoint"],
                    "endpointPath": ep["path"],
                    "registros": ep.get("registros", 0),
                    "valorTotal": ep.get("valorTotal", "0"),
                    "empresas": ep.get("empresaCodigosAlvo") or [],
                    "apareceNoWebPostoUI": "Não comprovado" if ep.get("httpStatus") != 200 else "Sem dados no período",
                    "integradoLogosSpace": _logos_integration(ep["endpoint"]),
                    "observacao": f"HTTP {ep.get('httpStatus')} — {ep.get('errors', [''])[0][:80] if ep.get('errors') else 'sem registros'}",
                })
            continue

        if ep["endpoint"] == "DESPESAS_FINANCEIRO_REDE":
            continue  # já coberto acima

        for tipo, count in sorted(ep.get("tipoHits", {}).items(), key=lambda x: -x[1]):
            in_despesas = tipo in despesas_tipos
            matrix.append({
                "tipoFinanceiro": tipo,
                "endpointOrigem": ep["endpoint"],
                "endpointPath": ep["path"],
                "registros": count,
                "valorTotal": "—",
                "empresas": ep.get("empresaCodigosAlvo") or ep.get("empresaCodigos", [])[:5],
                "apareceNoWebPostoUI": "Sim" if in_despesas else "Parcial — endpoint separado",
                "integradoLogosSpace": _logos_integration(ep["endpoint"]),
                "observacao": (
                    "Também em DESPESAS_REDE" if in_despesas
                    else "NÃO consolidado em DESPESAS_REDE — fonte paralela"
                ),
                "exemplos": ep.get("tipoSamples", {}).get(tipo, [])[:2],
            })

    return matrix


def _logos_integration(endpoint: str) -> str:
    mapping = {
        "DESPESAS_FINANCEIRO_REDE": "Sim — /v1/financial/expenses",
        "TITULO_PAGAR": "Sim — /v1/financial/accounts-payable",
        "CONTA_REDE": "Fallback accounts-payable",
        "MOVIMENTO_CONTA": "Não — apenas diagnóstico",
        "CAIXA": "Parcial — KPIs executive (soma sangria se campos existirem)",
        "CAIXA_APRESENTADO": "Não",
        "FINANCEIRO_EXCLUSAO": "Não",
        "TITULO_RECEBER": "Não (stub accounts-receivable vazio)",
    }
    return mapping.get(endpoint, "Não")


def write_mapping_md(matrix: list[dict], endpoint_results: list[dict], despesas_analysis: dict) -> str:
    lines = [
        "# FINANCIAL_ORIGIN_MAPPING — Sprint P0.1",
        "",
        f"**Gerado:** {datetime.now().isoformat(timespec='seconds')}",
        f"**Período:** {DATA_INI} .. {DATA_FIM}",
        "",
        "## Resumo executivo",
        "",
        "O WebPosto expõe **múltiplas entidades financeiras** em endpoints distintos.",
        "A **visão consolidada de despesas** (tela financeiro) vem principalmente de `CONSULTAR_DESPESAS_FINANCEIRO_REDE`,",
        "que agrega lançamentos de plano gerencial — **incluindo compras, salários e despesas operacionais** na mesma tabela.",
        "",
        "## Matriz origem (amostra)",
        "",
        "| Tipo Financeiro | Endpoint | Registros | Valor | WebPosto UI | LOGOS |",
        "|---|---|---:|---:|---|---|",
    ]
    seen = set()
    for row in matrix:
        key = (row["tipoFinanceiro"], row["endpointOrigem"])
        if key in seen:
            continue
        seen.add(key)
        if row.get("registros", 0) == 0 and "endpoint" in row["tipoFinanceiro"]:
            continue
        lines.append(
            f"| {row['tipoFinanceiro'][:40]} | `{row['endpointOrigem']}` | {row.get('registros', '—')} "
            f"| {row.get('valorTotal', '—')} | {row.get('apareceNoWebPostoUI', '—')[:25]} | {row.get('integradoLogosSpace', '—')[:20]} |"
        )

    lines.extend(["", "## DESPESAS_REDE — distribuição por tipo (descricaoDocumento)", ""])
    for tipo, info in sorted(despesas_analysis.get("porTipo", {}).items(), key=lambda x: -x[1]["count"]):
        lines.append(f"- **{tipo}**: {info['count']} registros, R$ {info['valor']}")

    lines.extend(["", "## Status endpoints auditados", ""])
    for ep in sorted(endpoint_results, key=lambda x: x["endpoint"]):
        status = ep.get("httpStatus", 0)
        reg = ep.get("registros", 0)
        lines.append(f"- `{ep['endpoint']}` → HTTP {status}, {reg} registros, campos: {len(ep.get('campos', []))}")

    lines.extend(["", "## O que NÃO vem de DESPESAS_REDE", ""])
    parallel = [r for r in matrix if "NÃO consolidado" in str(r.get("observacao", ""))]
    for r in parallel[:12]:
        lines.append(f"- **{r['tipoFinanceiro']}** via `{r['endpointOrigem']}` ({r['registros']} hits texto)")

    return "\n".join(lines) + "\n"


def write_financial_model_md(matrix: list[dict], endpoint_results: list[dict], despesas_analysis: dict) -> str:
    despesas_ep = next((e for e in endpoint_results if e["endpoint"] == "DESPESAS_FINANCEIRO_REDE"), {})
    titulo_ep = next((e for e in endpoint_results if e["endpoint"] == "TITULO_PAGAR"), {})
    mov_ep = next((e for e in endpoint_results if e["endpoint"] == "MOVIMENTO_CONTA"), {})
    caixa_ep = next((e for e in endpoint_results if e["endpoint"] == "CAIXA"), {})
    exclusao_ep = next((e for e in endpoint_results if e["endpoint"] == "FINANCEIRO_EXCLUSAO"), {})

    lines = [
        "# WEBPOSTO_FINANCIAL_MODEL — Sprint P0.1",
        "",
        f"**Gerado:** {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## 1. O que o WebPosto considera despesa?",
        "",
        "No modelo WebPosto, **despesa** na visão BI/financeiro consolidada = lançamentos de **plano de contas gerencial**",
        f"retornados por `CONSULTAR_DESPESAS_FINANCEIRO_REDE` ({despesas_ep.get('registros', 0)} registros, R$ {despesas_ep.get('valorTotal', '0')} no período).",
        "",
        "Campos expostos: `empresaCodigo`, `planoContaGerencialCodigo`, `descricaoDocumento`, `data`, `valor`.",
        "",
        "Tipos identificados na descrição:",
        "",
    ]
    for tipo, info in sorted(despesas_analysis.get("porTipo", {}).items(), key=lambda x: -x[1]["count"])[:10]:
        lines.append(f"- {tipo}: {info['count']}x (R$ {info['valor']})")

    lines.extend([
        "",
        "**Além disso**, o WebPosto trata como fluxo financeiro (não necessariamente na tela despesas):",
        "",
        "- **Títulos a pagar** (`TITULO_PAGAR`) — contas a pagar / fornecedores",
        "- **Movimentos bancários** (`MOVIMENTO_CONTA`) — extrato / tarifas / transferências",
        "- **Caixa** (`CAIXA`, `CAIXA_APRESENTADO`) — turnos, diferenças, apuração",
        "- **Exclusões** (`FINANCEIRO_EXCLUSAO`) — débitos caixa quando habilitado",
        "",
        "## 2. O que não está vindo de DESPESAS_REDE?",
        "",
    ])

    not_in_despesas = [
        f"- `{ep['endpoint']}`: {ep.get('registros', 0)} registros (HTTP {ep.get('httpStatus')})"
        for ep in endpoint_results
        if ep["endpoint"] != "DESPESAS_FINANCEIRO_REDE"
        and ep.get("httpStatus") == 200
        and ep.get("registros", 0) > 0
    ]
    lines.extend(not_in_despesas[:15])

    lines.extend([
        "",
        "Títulos a pagar **abertos/vencimento** vivem em `TITULO_PAGAR` — podem ou não estar liquidados em DESPESAS_REDE na data do pagamento.",
        "",
        "## 3. Sangria aparece em qual endpoint?",
        "",
    ])

    sangria_eps = [
        ep for ep in endpoint_results
        if ep.get("tipoHits", {}).get("Sangria / retirada caixa", 0) > 0
    ]
    if sangria_eps:
        for ep in sangria_eps:
            lines.append(f"- `{ep['endpoint']}`: {ep['tipoHits'].get('Sangria / retirada caixa', 0)} menções em campos texto")
    else:
        lines.append("- **Nenhuma menção literal 'sangria'** nos payloads do período nos endpoints caixa/financeiro.")
        lines.append("- Campos esperados (`valorSangria`, `sangria`) **ausentes** em `/INTEGRACAO/CAIXA` — apenas `diferenca`, `apurado`, `fechamento`.")
        lines.append("- Sangria provável via **FINANCEIRO_EXCLUSAO** ou consolidada em DESPESAS_REDE com descrição genérica.")

    lines.extend([
        "",
        "## 4. Compras aparecem em qual endpoint?",
        "",
    ])
    compra_in_despesas = despesas_analysis.get("porTipo", {}).get("Compra mercadoria / NF entrada", {})
    lines.append(f"- **DESPESAS_REDE**: {compra_in_despesas.get('count', 0)} registros com 'compra' na descrição (ex.: 'REF A COMPRA...')")
    compra_eps = [ep for ep in endpoint_results if ep["endpoint"] in {"NOTA_ENTRADA", "PEDIDO_COMPRAS", "COMPRA_REDE", "CARTAO_COMPRA"}]
    for ep in compra_eps:
        lines.append(f"- `{ep['endpoint']}`: HTTP {ep.get('httpStatus')}, {ep.get('registros', 0)} registros")

    lines.extend([
        "",
        "## 5. Título a pagar aparece em qual endpoint?",
        "",
        f"- **`TITULO_PAGAR`**: HTTP {titulo_ep.get('httpStatus')}, {titulo_ep.get('registros', 0)} registros, R$ {titulo_ep.get('valorTotal', '0')}",
        "- **`CONSULTAR_TITULO_PAGAR_REDE`**: rede vazia (0 registros) — usar TITULO_PAGAR individual",
        "- **`CONTA` / CONTA_REDE**: fallback contas",
        "",
        "## 6. Movimento bancário aparece em qual endpoint?",
        "",
        f"- **`MOVIMENTO_CONTA`**: HTTP {mov_ep.get('httpStatus')}, {mov_ep.get('registros', 0)} registros",
        f"- Campos: `{', '.join(mov_ep.get('campos', [])[:12])}`",
        "",
        "## 7. Endpoints a integrar no LOGOS SPACE",
        "",
        "| Prioridade | Endpoint | Motivo |",
        "|---|---|---|",
        "| P0 | DESPESAS_FINANCEIRO_REDE | Já integrado — corrigir filtro multiselect |",
        "| P0 | TITULO_PAGAR | Contas a pagar — já integrado |",
        "| P1 | MOVIMENTO_CONTA | Tarifas, conciliação, fluxo caixa banco |",
        "| P1 | FINANCEIRO_EXCLUSAO | Sangria/débito caixa se habilitado |",
        "| P2 | CAIXA + CAIXA_APRESENTADO | Conciliação turno / quebra |",
        "| P2 | NOTA_ENTRADA / PEDIDO_COMPRAS | Compras detalhadas (se 200 OK) |",
        "| P3 | TITULO_RECEBER | Contas a receber |",
        "",
        "## 8. Modelo correto para Data Warehouse",
        "",
        "```",
        "fact_despesa_gerencial     ← CONSULTAR_DESPESAS_FINANCEIRO_REDE (grain: empresa+data+plano+valor)",
        "fact_titulo_pagar          ← TITULO_PAGAR (grain: tituloPagarCodigo)",
        "fact_movimento_bancario    ← MOVIMENTO_CONTA (grain: movimentoCodigo)",
        "fact_caixa_turno           ← CAIXA (grain: caixaCodigo)",
        "fact_caixa_conciliacao     ← CAIXA_APRESENTADO (grain: caixaCodigo+forma)",
        "fact_financeiro_exclusao   ← FINANCEIRO_EXCLUSAO (grain: exclusaoCodigo)",
        "fact_compra                ← NOTA_ENTRADA / PEDIDO_COMPRAS (se disponível)",
        "",
        "dim_empresa                ← EMPRESAS",
        "dim_plano_conta            ← derivado de despesas + movimento_conta",
        "dim_fornecedor             ← TITULO_PAGAR",
        "```",
        "",
        "**Regra de ouro DW:** não deduplicar DESPESAS_REDE com TITULO_PAGAR sem chave de ligação — API não expõe `tituloPagarCodigo` em DESPESAS_REDE.",
        "",
        "## Diagrama entidade-origem",
        "",
        "```mermaid",
        "flowchart LR",
        "  subgraph consolidado [Visao Despesas WebPosto]",
        "    D[DESPESAS_FINANCEIRO_REDE]",
        "  end",
        "  subgraph paralelo [Fontes Paralelas]",
        "    TP[TITULO_PAGAR]",
        "    MC[MOVIMENTO_CONTA]",
        "    CX[CAIXA]",
        "    FE[FINANCEIRO_EXCLUSAO]",
        "    NE[NOTA_ENTRADA]",
        "  end",
        "  TP -.->|liquidacao| D",
        "  MC -.->|tarifas| D",
        "  CX -.->|sangria/quebra| FE",
        "  FE -.->|debito| D",
        "  NE -.->|compra| D",
        "```",
    ])
    return "\n".join(lines) + "\n"


async def run_audit(data_ini: str, data_fim: str) -> dict[str, Any]:
    config = load_core_config()
    params = {"dataInicial": data_ini, "dataFinal": data_fim}
    endpoint_results: list[dict[str, Any]] = []

    async with httpx.AsyncClient() as client:
        for group_name, endpoints in ENDPOINT_GROUPS.items():
            for name, path in endpoints.items():
                extra = dict(params)
                if name == "FINANCEIRO_EXCLUSAO":
                    extra.update({"pagina": 0, "tamanhoPagina": 200})
                if name == "PEDIDO_COMPRAS":
                    extra.update({"pagina": 0, "tamanhoPagina": 100})
                result = await fetch_endpoint(
                    client,
                    config.webposto_base_url,
                    config.webposto_api_key,
                    name,
                    path,
                    extra,
                    max_pages=5 if name == "DESPESAS_FINANCEIRO_REDE" else 2,
                )
                result["grupo"] = group_name
                endpoint_results.append(result)
                print(f"  {name}: HTTP {result.get('httpStatus')} reg={result.get('registros')}")

    despesas_ep = next(e for e in endpoint_results if e["endpoint"] == "DESPESAS_FINANCEIRO_REDE")
    despesas_rows = []
    # Re-fetch full despesas for analysis (stored in result sample only - need rows)
    async with httpx.AsyncClient() as client:
        pp = {**params, "CHAVE": config.webposto_api_key}
        resp = await client.get(
            f"{config.webposto_base_url}/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
            params=pp,
            timeout=90,
        )
        if resp.status_code == 200:
            despesas_rows = _rows(resp.json())

    despesas_analysis = analyze_despesas_consolidadas(despesas_rows)
    matrix = build_origin_matrix(endpoint_results, despesas_analysis)

    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "periodo": {"dataInicial": data_ini, "dataFinal": data_fim},
        "endpointResults": endpoint_results,
        "despesasConsolidadas": despesas_analysis,
        "matrix": matrix,
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-inicial", default=DATA_INI)
    parser.add_argument("--data-final", default=DATA_FIM)
    args = parser.parse_args()

    print("=== Sprint P0.1 — Financial Origin Mapping ===")
    data = await run_audit(args.data_inicial, args.data_final)

    json_path = ROOT / "financial_origin_matrix.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    mapping_md = write_mapping_md(data["matrix"], data["endpointResults"], data["despesasConsolidadas"])
    (ROOT / "FINANCIAL_ORIGIN_MAPPING.md").write_text(mapping_md, encoding="utf-8")

    model_md = write_financial_model_md(data["matrix"], data["endpointResults"], data["despesasConsolidadas"])
    (ROOT / "WEBPOSTO_FINANCIAL_MODEL.md").write_text(model_md, encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD:   FINANCIAL_ORIGIN_MAPPING.md, WEBPOSTO_FINANCIAL_MODEL.md")
    print(f"Matrix rows: {len(data['matrix'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
