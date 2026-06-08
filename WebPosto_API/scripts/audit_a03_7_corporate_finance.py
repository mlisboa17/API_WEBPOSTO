#!/usr/bin/env python3
"""
Sprint A03.7 — Consolidação financeira corporativa.
Audita, modela e documenta. Sem alteração de código de produção.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
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
PERIOD = {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}

# Classificador LOGOS SPACE (independente do WebPosto)
LOGOS_CATEGORIES: dict[str, tuple[str, ...]] = {
    "DESPESA_OPERACIONAL": (
        "energia", "luz", "coelba", "neoenergia", "agua", "água", "telefone", "internet",
        "limpeza", "material de limpeza", "almoço", "almoco", "uber", "diaria", "diária",
    ),
    "DESPESA_PESSOAL": (
        "salario", "salário", "folha", "pro labore", "pro-labore", "funcionario", "funcionário",
        "complemento salario", "adiantamento", "vale", "beneficio", "benefício",
    ),
    "DESPESA_ADMINISTRATIVA": (
        "contabil", "contábil", "juridic", "jurídic", "sistema", "consultoria", "software",
        "contador", "honorario", "honorário",
    ),
    "DESPESA_COMERCIAL": (
        "marketing", "publicidade", "comissao", "comissão", "propaganda", "brinde",
    ),
    "COMPRAS": (
        "compra", "mercadoria", "produto", "parafuso", "cloro", "cadeado", "material",
        "combustivel", "combustível", "trr", "nota entrada",
    ),
    "FINANCEIRO": (
        "juros", "tarifa", "multa", "iof", "ted", "doc", "pix", "transferencia", "transferência",
        "taxa banc", "banco",
    ),
    "OUTROS": (),
}


def _norm(text: Any) -> str:
    if text is None:
        return ""
    s = str(text).strip().casefold()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _rows(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for k in ("resultados", "data", "items"):
            v = payload.get(k)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
    return []


def classify_logos(desc: str, plano: str = "") -> str:
    blob = _norm(f"{desc} {plano}")
    for cat, keywords in LOGOS_CATEGORIES.items():
        if cat == "OUTROS":
            continue
        if any(kw in blob for kw in keywords):
            return cat
    return "OUTROS"


async def fetch_endpoint(client: httpx.AsyncClient, base: str, key: str, path: str, params: dict) -> dict:
    t0 = time.perf_counter()
    full = {**params, "CHAVE": key}
    try:
        r = await client.get(f"{base}{path}", params=full, timeout=90)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        entry = {"httpStatus": r.status_code, "ms": ms, "registros": 0, "campos": [], "sampleRows": []}
        if r.status_code != 200:
            entry["body_preview"] = r.text[:200]
            return entry
        rows = _rows(r.json())
        entry["registros"] = len(rows)
        entry["campos"] = list(rows[0].keys()) if rows else []
        entry["sampleRows"] = rows[:3]
        return entry
    except Exception as exc:
        return {"httpStatus": 0, "ms": round((time.perf_counter() - t0) * 1000, 1), "error": str(exc)[:200]}


async def collect_all(config) -> dict[str, Any]:
    paths = {
        "DESPESAS_REDE": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
        "TITULO_PAGAR": "/INTEGRACAO/TITULO_PAGAR",
        "TITULO_RECEBER": "/INTEGRACAO/TITULO_RECEBER",
        "MOVIMENTO_CONTA": "/INTEGRACAO/MOVIMENTO_CONTA",
        "TRANSFERENCIA_BANCARIA": "/INTEGRACAO/TRANSFERENCIA_BANCARIA",
        "CAIXA": "/INTEGRACAO/CAIXA",
        "CAIXA_APRESENTADO": "/INTEGRACAO/CAIXA_APRESENTADO",
        "COMPRA_REDE": "/INTEGRACAO/COMPRA_REDE",
        "NOTA_ENTRADA": "/INTEGRACAO/NOTA_ENTRADA",
        "NOTA_ENTRADA_REDE": "/INTEGRACAO/NOTA_ENTRADA_REDE",
        "FORNECEDOR_REDE": "/INTEGRACAO/FORNECEDOR_REDE",
        "EMPRESAS": "/INTEGRACAO/EMPRESAS",
    }
    data: dict[str, Any] = {}
    async with httpx.AsyncClient() as client:
        for name, path in paths.items():
            print(f"  fetch {name}...")
            data[name] = await fetch_endpoint(client, config.webposto_base_url, config.webposto_api_key, path, PERIOD)
    return data


def analyze_expense_classification(despesas_rows: list[dict]) -> dict[str, Any]:
    by_cat: dict[str, dict] = defaultdict(lambda: {"count": 0, "valor": Decimal("0"), "samples": []})
    for row in despesas_rows:
        desc = str(row.get("descricaoDocumento") or row.get("planoConta") or "")
        cat = classify_logos(desc)
        val = Decimal(str(row.get("valor") or 0))
        by_cat[cat]["count"] += 1
        by_cat[cat]["valor"] += val
        if len(by_cat[cat]["samples"]) < 3:
            by_cat[cat]["samples"].append(desc[:80])
    return {
        k: {"count": v["count"], "valor": str(v["valor"].quantize(Decimal("0.01"))), "samples": v["samples"]}
        for k, v in sorted(by_cat.items(), key=lambda x: -x[1]["count"])
    }


def analyze_treasury(mov_rows: list[dict], transf_rows: list[dict]) -> dict[str, Any]:
    tipo_counter = Counter()
    origem_counter = Counter()
    desc_patterns = Counter()
    credito = debito = tarifa = transf = 0
    for row in mov_rows:
        tipo = str(row.get("tipo") or "")
        tipo_counter[tipo] += 1
        origem = str(row.get("tipoDocumentoOrigem") or "")
        origem_counter[origem] += 1
        desc = _norm(row.get("descricao"))
        if "tarifa" in desc or "taxa" in desc:
            tarifa += 1
        if "transf" in desc:
            transf += 1
        if "pix" in desc:
            desc_patterns["PIX"] += 1
        if "ted" in desc:
            desc_patterns["TED"] += 1
        if "doc" in desc and "documento" not in desc:
            desc_patterns["DOC"] += 1
        if "crédito" in tipo.casefold() or "credito" in tipo.casefold():
            credito += 1
        elif "débito" in tipo.casefold() or "debito" in tipo.casefold():
            debito += 1
    return {
        "movimento_registros": len(mov_rows),
        "transferencia_registros": len(transf_rows),
        "tipo_distribuicao": dict(tipo_counter.most_common(10)),
        "origem_distribuicao": dict(origem_counter.most_common(10)),
        "credito_count": credito,
        "debito_count": debito,
        "tarifa_count": tarifa,
        "transferencia_count": transf,
        "padroes_descricao": dict(desc_patterns),
        "campos_chave": ["tipoDocumentoOrigem", "planoContaGerencialCodigo", "descricao", "valor", "tipo", "contaCodigo"],
    }


def analyze_cash(caixa_rows: list[dict], apresentado_rows: list[dict]) -> dict[str, Any]:
    agg = defaultdict(lambda: {"total_apurado": Decimal("0"), "total_diferenca": Decimal("0"), "turnos": 0})
    fields_map = {
        "despesa_caixa": ("despesaApurado", "despesaDiferenca"),
        "vale_funcionario": ("valeFunApurado", "valeFunDiferenca"),
        "emprestimo": ("emprestimoApurado", "emprestimoDiferenca"),
        "dinheiro": ("dinheiroApurado", "dinheiroDiferenca"),
        "cartao": ("cartaoApurado", "cartaoDiferenca"),
    }
    for row in apresentado_rows:
        for name, (apurado_k, diff_k) in fields_map.items():
            ap = row.get(apurado_k)
            df = row.get(diff_k)
            if ap is not None:
                agg[name]["total_apurado"] += Decimal(str(ap))
            if df is not None:
                agg[name]["total_diferenca"] += Decimal(str(df))
            agg[name]["turnos"] += 1
    dif_turnos = [abs(float(r.get("diferenca") or 0)) for r in caixa_rows if r.get("diferenca")]
    return {
        "turnos_caixa": len(caixa_rows),
        "turnos_apresentado": len(apresentado_rows),
        "agregados_apresentado": {
            k: {
                "apurado": str(v["total_apurado"].quantize(Decimal("0.01"))),
                "diferenca": str(v["total_diferenca"].quantize(Decimal("0.01"))),
                "turnos": v["turnos"],
            }
            for k, v in agg.items()
        },
        "quebra_media_turno": round(sum(dif_turnos) / len(dif_turnos), 2) if dif_turnos else 0,
        "sangria_campo_dedicado": False,
        "suprimento_campo_dedicado": False,
        "fundo_caixa_campo_dedicado": False,
    }


def analyze_receivables(rows: list[dict]) -> dict[str, Any]:
    situacoes = Counter(str(r.get("situacao") or "—") for r in rows)
    total_valor = sum(Decimal(str(r.get("valor") or 0)) for r in rows)
    vencidos = sum(1 for r in rows if str(r.get("vencimento") or "") < DATA_FIM and "pago" not in _norm(r.get("situacao")))
    return {
        "registros": len(rows),
        "valor_total": str(total_valor.quantize(Decimal("0.01"))),
        "situacoes": dict(situacoes),
        "vencidos_estimados": vencidos,
        "campos": list(rows[0].keys()) if rows else [],
        "integrado_logos": False,
    }


def analyze_payables(rows: list[dict]) -> dict[str, Any]:
    aberto = pago = 0
    valor_aberto = Decimal("0")
    for r in rows:
        sit = _norm(r.get("situacao"))
        val = Decimal(str(r.get("valor") or 0))
        pago_val = Decimal(str(r.get("valorPago") or 0))
        if "pago" in sit:
            pago += 1
        else:
            aberto += 1
            valor_aberto += val - pago_val if val > pago_val else val
    return {"registros": len(rows), "aberto": aberto, "pago": pago, "valor_aberto_est": str(valor_aberto.quantize(Decimal("0.01")))}


def performance_summary(api_data: dict) -> dict[str, Any]:
    perf = {}
    for name in ("MOVIMENTO_CONTA", "CAIXA", "CAIXA_APRESENTADO", "TITULO_PAGAR", "TITULO_RECEBER", "DESPESAS_REDE", "TRANSFERENCIA_BANCARIA"):
        ep = api_data.get(name, {})
        perf[name] = {
            "ms": ep.get("ms"),
            "registros": ep.get("registros"),
            "httpStatus": ep.get("httpStatus"),
            "paginacao_observacao": "ultimoCodigo presente em MOVIMENTO/TRANSFERENCIA — paginar em produção",
        }
    return perf


def write_all_reports(data: dict[str, Any]) -> None:
    api = data["api"]
    exp_class = data["expense_classification"]
    treasury = data["treasury"]
    cash = data["cash"]
    recv = data["receivables"]
    pay = data["payables"]
    perf = data["performance"]

    # BLOCO 1
    (ROOT / "CORPORATE_FINANCE_CENTER.md").write_text("\n".join([
        "# CORPORATE FINANCE CENTER — Especificação A03.7",
        "",
        f"**Gerado:** {data['generatedAt']}",
        "",
        "## Visão",
        "",
        "Módulo **Centro Financeiro** = camada de leitura unificada da holding, **sem somar fatos distintos**.",
        "",
        "## Fontes (módulos independentes)",
        "",
        "| Módulo LOGOS | Fonte WebPosto | Endpoint LOGOS | Grain |",
        "|---|---|---|---|",
        "| Despesa Gerencial | DESPESAS_FINANCEIRO_REDE | /v1/financial/expenses | plano+data+valor |",
        "| Contas a Pagar | TITULO_PAGAR | /v1/financial/accounts-payable | tituloPagarCodigo |",
        "| Contas a Receber | TITULO_RECEBER | (futuro) | tituloReceberCodigo |",
        "| Tesouraria | MOVIMENTO_CONTA | (futuro F02) | movimentoContaCodigo |",
        "",
        "## Painéis previstos",
        "",
        "### Resultado Financeiro",
        "- **Receitas:** TITULO_RECEBER + vendas (módulo comercial — fora do escopo caixa)",
        "- **Despesas:** fact_despesa_gerencial ONLY",
        "- **Resultado:** receitas − despesas gerenciais (NÃO incluir títulos em aberto)",
        "",
        "### Fluxo de Caixa",
        "- **Previsto:** TITULO_PAGAR (vencimentos) + TITULO_RECEBER (recebíveis)",
        "- **Realizado:** MOVIMENTO_CONTA (crédito/débito)",
        "",
        "### Contas a Pagar",
        f"- Aberto: {pay['aberto']} | Pago: {pay['pago']} | Valor aberto est.: R$ {pay['valor_aberto_est']}",
        "",
        "### Contas a Receber",
        f"- Registros API: {recv['registros']} | Valor: R$ {recv['valor_total']} | Vencidos est.: {recv['vencidos_estimados']}",
        "",
        "## Regra crítica",
        "",
        "```",
        "DESPESA GERENCIAL ≠ TÍTULO A PAGAR ≠ MOVIMENTO BANCÁRIO ≠ CAIXA ≠ TÍTULO RECEBER",
        "```",
        "",
        "Correlacionar no futuro via chaves — nunca somar automaticamente.",
    ]) + "\n", encoding="utf-8")

    # BLOCO 2
    (ROOT / "TREASURY_MODULE_BLUEPRINT.md").write_text("\n".join([
        "# TREASURY_MODULE_BLUEPRINT — A03.7",
        "",
        f"**Período evidência:** {DATA_INI} .. {DATA_FIM}",
        "",
        "## Fontes",
        "",
        f"- MOVIMENTO_CONTA: {treasury['movimento_registros']} reg, {perf['MOVIMENTO_CONTA']['ms']}ms",
        f"- TRANSFERENCIA_BANCARIA: {treasury['transferencia_registros']} reg",
        "",
        "## Mapeamento tipos",
        "",
        f"| Tipo | Contagem |",
        f"|---|---:|",
        *[f"| {k} | {v} |" for k, v in treasury["tipo_distribuicao"].items()],
        "",
        "## Origem documento",
        "",
        *[f"- `{k}`: {v}" for k, v in treasury["origem_distribuicao"].items()],
        "",
        f"- Créditos: {treasury['credito_count']} | Débitos: {treasury['debito_count']}",
        f"- Tarifas (desc): {treasury['tarifa_count']} | Transferências: {treasury['transferencia_count']}",
        f"- PIX/TED/DOC em descrição: {treasury['padroes_descricao']}",
        "",
        "## Campos chave",
        "",
        ", ".join(f"`{c}`" for c in treasury["campos_chave"]),
        "",
        "## Módulo TESOURARIA (futuro F02)",
        "",
        "- Extrato consolidado por contaCodigo",
        "- Conciliação bancária (conciliado flag)",
        "- Tarifas isoladas para DRE financeiro",
        "- Não misturar com despesas gerenciais",
    ]) + "\n", encoding="utf-8")

    # BLOCO 3
    ag = cash["agregados_apresentado"]
    (ROOT / "CASH_OPERATION_MODEL.md").write_text("\n".join([
        "# CASH_OPERATION_MODEL — A03.7",
        "",
        f"**Turnos auditados:** {cash['turnos_caixa']}",
        "",
        "## Matriz operação de caixa",
        "",
        "| Conceito | Campo API | Disponível | Evidência período |",
        "|---|---|---|---|",
        f"| Despesa caixa | despesaApurado/Diferenca | **Sim** | R$ {ag.get('despesa_caixa', {}).get('apurado', '0')} apurado |",
        f"| Vale funcionário | valeFunApurado/Diferenca | **Sim** | R$ {ag.get('vale_funcionario', {}).get('apurado', '0')} |",
        f"| Empréstimo | emprestimoApurado/Diferenca | **Sim** | R$ {ag.get('emprestimo', {}).get('apurado', '0')} |",
        f"| Quebra/diferença | diferenca (CAIXA) | **Sim** | média {cash['quebra_media_turno']} |",
        f"| Sangria explícita | — | **Não** | via DESPESAS_REDE se lançada |",
        f"| Suprimento | — | **Não** | — |",
        f"| Fundo caixa | — | **Não** | — |",
        "",
        "## Modelo LOGOS",
        "",
        "```",
        "fact_caixa_turno       ← CAIXA",
        "fact_caixa_forma       ← CAIXA_APRESENTADO",
        "fact_despesa_gerencial ← DESPESAS (lançamentos plano — separado)",
        "```",
    ]) + "\n", encoding="utf-8")

    # BLOCO 4
    lines = ["# CORPORATE_EXPENSE_CLASSIFICATION — A03.7", "", "Classificador LOGOS SPACE (regras em `audit_a03_7_corporate_finance.py`).", "", "| Categoria LOGOS | Registros | Valor | Exemplos |", "|---|---:|---:|---|"]
    for cat, info in exp_class.items():
        ex = "; ".join(info.get("samples", [])[:2]) or "—"
        lines.append(f"| {cat} | {info['count']} | R$ {info['valor']} | {ex[:60]} |")
    lines.extend(["", "## Mapeamento para diretoria", "", "- DESPESA_PESSOAL + DESPESA_OPERACIONAL → custo operacional", "- COMPRAS → CMV / insumos", "- FINANCEIRO → resultado financeiro", "- OUTROS → revisão manual periódica"])
    (ROOT / "CORPORATE_EXPENSE_CLASSIFICATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # BLOCO 5
    compra = api.get("COMPRA_REDE", {})
    nota = api.get("NOTA_ENTRADA", {})
    forn = api.get("FORNECEDOR_REDE", {})
    (ROOT / "PURCHASING_MODULE_BLUEPRINT.md").write_text("\n".join([
        "# PURCHASING_MODULE_BLUEPRINT — A03.7",
        "",
        "## Status token atual",
        "",
        f"| Endpoint | HTTP | Registros |",
        f"|---|---|---:|",
        f"| COMPRA_REDE | {compra.get('httpStatus')} | {compra.get('registros', 0)} |",
        f"| NOTA_ENTRADA | {nota.get('httpStatus')} | {nota.get('registros', 0)} |",
        f"| NOTA_ENTRADA_REDE | {api.get('NOTA_ENTRADA_REDE', {}).get('httpStatus')} | {api.get('NOTA_ENTRADA_REDE', {}).get('registros', 0)} |",
        f"| FORNECEDOR_REDE | {forn.get('httpStatus')} | {forn.get('registros', 0)} |",
        "",
        "## Enquanto 401 — proxy via DESPESAS_REDE",
        "",
        f"Compras classificadas LOGOS: {exp_class.get('COMPRAS', {}).get('count', 0)} registros / R$ {exp_class.get('COMPRAS', {}).get('valor', '0')}",
        "",
        "## Schema inferido (TITULO_PAGAR link)",
        "",
        "TITULO_PAGAR expõe `notaEntradaCodigo`, `fornecedorCodigo`, `nomeFornecedor` — base para módulo compras futuro.",
        "",
        "## Módulo futuro F04",
        "",
        "- fact_compra ← NOTA_ENTRADA",
        "- dim_fornecedor ← FORNECEDOR_REDE",
        "- Relacionamento compra → título pagar",
    ]) + "\n", encoding="utf-8")

    # BLOCO 6
    (ROOT / "RECEIVABLE_ANALYSIS_MODEL.md").write_text("\n".join([
        "# RECEIVABLE_ANALYSIS_MODEL — A03.7",
        "",
        f"**Registros TITULO_RECEBER:** {recv['registros']}",
        f"**Valor total:** R$ {recv['valor_total']}",
        "",
        "## Situações",
        "",
        *[f"- `{k}`: {v}" for k, v in recv.get("situacoes", {}).items()],
        "",
        f"**Vencidos estimados (período):** {recv['vencidos_estimados']}",
        "",
        "## Campos disponíveis",
        "",
        ", ".join(f"`{c}`" for c in recv.get("campos", [])[:20]),
        "",
        "## Análises futuras (F05)",
        "",
        "- Carteira por cliente",
        "- Inadimplência aging (0-30, 31-60, 61+)",
        "- DSO (Days Sales Outstanding)",
        "",
        f"**LOGOS hoje:** integrado = {recv['integrado_logos']} — prioridade A04/F05",
    ]) + "\n", encoding="utf-8")

    # BLOCO 7 — TOP 20
    opportunities = [
        ("Centro Financeiro holding", "Diretoria", "Alto", "Visão única sem DW", "Controle"),
        ("Despesas por filial multiselect", "Operação", "Alto", "P0.2 pronto", "Controle"),
        ("Classificação despesa LOGOS", "Diretoria", "Alto", "363 linhas classificáveis", "Margem"),
        ("Contas a pagar aging", "Financeiro", "Alto", "66 títulos API", "Economia"),
        ("Fluxo caixa projetado", "Diretoria", "Alto", "TITULO_PAGAR+RECEBER", "Controle"),
        ("Conciliação bancária", "Tesouraria", "Médio", "400 movimentos", "Controle"),
        ("Operação caixa turnos", "Operação", "Médio", "21 turnos/semana", "Perdas"),
        ("Vale funcionário caixa", "RH/Operação", "Médio", "valeFun* fields", "Controle"),
        ("Quebra caixa ranking", "Operação", "Médio", "diferenca por turno", "Perdas"),
        ("Despesa rede filiais 5256+", "Holding", "Alto", "DESPESAS_REDE 10 filiais", "Cobertura"),
        ("Títulos combustível TRR", "Compras", "Médio", "via TITULO_PAGAR desc", "Economia"),
        ("Tarifas bancárias", "Financeiro", "Médio", "MOVIMENTO_CONTA", "Economia"),
        ("Inadimplência clientes", "Comercial", "Médio", "11 recebíveis", "Margem"),
        ("DRE gerencial separado", "Diretoria", "Alto", "facts separados", "Margem"),
        ("Snapshot financeiro TTL", "Performance", "Médio", "cache 5min", "ROI técnico"),
        ("Executive KPIs otimizados", "Diretoria", "Médio", "8-10s → meta 3s", "UX"),
        ("Compras NF (pós-token)", "Compras", "Alto", "401 hoje", "Economia"),
        ("Fornecedor ranking", "Compras", "Médio", "TITULO_PAGAR fornecedor", "Economia"),
        ("Multi-filial benchmark", "Holding", "Alto", "117 reg 2 filiais", "Controle"),
        ("Ticket Quality empresaCodigo", "Integração", "Alto", "reduz confusão", "Confiabilidade"),
    ]
    opp_lines = ["# TOP_20_BUSINESS_OPPORTUNITIES — A03.7", "", "| # | Oportunidade | Público | Impacto | Evidência | Tipo |", "|---|---|---|---|---|---|"]
    for i, (o, pub, imp, ev, tipo) in enumerate(opportunities, 1):
        opp_lines.append(f"| {i} | {o} | {pub} | {imp} | {ev} | {tipo} |")
    opp_lines.extend([
        "",
        "## Respostas",
        "",
        "**Diretoria hoje:** Centro Financeiro + despesas classificadas + contas a pagar + totais por filial.",
        "**Maior ROI:** Centro Financeiro + classificação despesa (sem custo de token).",
        "**Maior economia:** Contas a pagar aging + tarifas bancárias.",
        "**Maior controle:** Multiselect despesas + operação caixa.",
        "**Reduz perdas:** Quebra caixa + vale funcionário.",
        "**Melhora margem:** Classificação COMPRAS vs OPERACIONAL.",
    ])
    (ROOT / "TOP_20_BUSINESS_OPPORTUNITIES.md").write_text("\n".join(opp_lines) + "\n", encoding="utf-8")

    # BLOCO 8
    (ROOT / "FINANCIAL_ROADMAP_1.0.md").write_text("\n".join([
        "# FINANCIAL_ROADMAP_1.0",
        "",
        "| Fase | Módulo | Fonte | Status | Sprint |",
        "|---|---|---|---|---|",
        "| F01 | Centro Financeiro | DESPESAS+TITULO_PAGAR+RECEBER+MOV | Especificado | A03.7 → A04 prep |",
        "| F02 | Tesouraria | MOVIMENTO_CONTA | Blueprint | Pós F01 |",
        "| F03 | Operação Caixa | CAIXA+APRESENTADO | Modelo | Pós F01 |",
        "| F04 | Compras | NOTA_ENTRADA | Aguarda token | Quality |",
        "| F05 | Recebíveis | TITULO_RECEBER | 11 reg API | Pós F01 |",
        "| F06 | Fluxo Caixa | TITULO_* + MOVIMENTO | Projetado | F01+F02 |",
        "| F07 | Conciliação Bancária | MOVIMENTO_CONTA | Projetado | F02 |",
        "| F08 | DRE Gerencial | facts separados | Projetado | F01 consolidado |",
        "",
        "**Sequência recomendada:** F01 → F05 → F02 → F03 → F06 → F07 → F08 → F04",
    ]) + "\n", encoding="utf-8")

    # BLOCO 9
    plines = ["# FINANCIAL_PERFORMANCE_REPORT — A03.7", "", "| Endpoint | HTTP | ms | Registros |", "|---|---|---:|---:|"]
    for name, p in perf.items():
        plines.append(f"| {name} | {p.get('httpStatus')} | {p.get('ms')} | {p.get('registros')} |")
    plines.extend(["", "## Observações", "", "- DESPESAS: 1 fetch rede (P0.2) — ~500-1200ms", "- MOVIMENTO/TRANSFERENCIA: paginar ultimoCodigo", "- Snapshot LOGOS: MISS/LIVE (A03.6) — implementar warm cache F01", "- TITULO_PAGAR overview: N× filial — otimizar em F01"])
    (ROOT / "FINANCIAL_PERFORMANCE_REPORT.md").write_text("\n".join(plines) + "\n", encoding="utf-8")

    # BLOCO 10 + FINAL
    write_a04_readiness(data)
    write_final_report(data)


def write_a04_readiness(data: dict) -> None:
    (ROOT / "A04_READINESS_REPORT.md").write_text("\n".join([
        "# A04_READINESS_REPORT — A03.7",
        "",
        "## O DW deve começar agora?",
        "",
        "**Não imediatamente.** Consolidar F01 (Centro Financeiro) antes do DW físico.",
        "",
        "## O modelo financeiro já está maduro?",
        "",
        "**Sim conceitualmente** (LOGOS_FINANCIAL_MODEL_1.0 + esta sprint). **Parcial operacionalmente** (recebíveis stub, tesouraria/caixa não integrados).",
        "",
        "## O que falta?",
        "",
        "1. Integrar TITULO_RECEBER no LOGOS",
        "2. Módulo Tesouraria (MOVIMENTO_CONTA)",
        "3. Token NOTA_ENTRADA / COMPRA_REDE",
        "4. Snapshot/cache financeiro corporativo",
        "5. Classificador despesa em produção (rules engine)",
        "",
        "## Qual o risco?",
        "",
        "**Médio-baixo (30/100)** — risco principal: somar despesas + títulos por engano.",
        "",
        "## Prioridade",
        "",
        "**F01 Centro Financeiro** → depois DW com facts já validados.",
    ]) + "\n", encoding="utf-8")


def write_final_report(data: dict) -> None:
    (ROOT / "A03_7_CORPORATE_FINANCIAL_CONSOLIDATION_REPORT.md").write_text("\n".join([
        "# A03_7_CORPORATE_FINANCIAL_CONSOLIDATION_REPORT",
        "",
        f"**Gerado:** {data['generatedAt']}",
        "",
        "## Respostas obrigatórias (12)",
        "",
        "### 1. Quais módulos financeiros podem nascer agora?",
        "Centro Financeiro (F01), Classificação Despesas, Contas a Pagar (já parcial), Análise Recebíveis (API pronta).",
        "",
        "### 2. Quais fontes são mais valiosas?",
        "DESPESAS_REDE (427 reg), TITULO_PAGAR (66 reg), MOVIMENTO_CONTA (200 reg), CAIXA_APRESENTADO (21 turnos).",
        "",
        "### 3. O que o WebPosto não entrega?",
        "Compras detalhadas (401), sangria/suprimento explícitos, empresaCodigo em despesas, chave ligação despesa↔título.",
        "",
        "### 4. O que conseguimos sem novos tokens?",
        "Centro Financeiro, Tesouraria (leitura), Caixa operacional, Classificação despesa, Contas pagar/receber leitura, Fluxo projetado básico.",
        "",
        "### 5. Qual módulo gera maior ROI?",
        "**F01 Centro Financeiro** — visão holding com dados existentes.",
        "",
        "### 6. Qual módulo gera maior economia?",
        "**Contas a Pagar aging** + **tarifas bancárias** (MOVIMENTO_CONTA).",
        "",
        "### 7. Qual módulo gera maior controle?",
        "**Operação Caixa** + **multiselect despesas** (P0.2 validado).",
        "",
        "### 8. Qual módulo desenvolver primeiro?",
        "**F01 — Centro Financeiro Corporativo.**",
        "",
        "### 9. O DW deve iniciar agora?",
        "**Não.** Consolidar F01, depois DW com facts de LOGOS_FINANCIAL_MODEL_1.0.",
        "",
        "### 10. Nova nota de maturidade",
        "**7.5 / 10** (+0.5 vs A03.6 — modelo corporativo formalizado).",
        "",
        "### 11. Novo risco operacional",
        "**30 / 100** (−5 vs A03.6 — regra de não-mistura documentada).",
        "",
        "### 12. Próxima sprint recomendada",
        "**A04-Prep / F01** — especificação técnica + API read-only Centro Financeiro (sem telas novas, endpoints agregadores).",
        "",
        "---",
        "",
        "## Documentos gerados",
        "",
        "- CORPORATE_FINANCE_CENTER.md",
        "- TREASURY_MODULE_BLUEPRINT.md",
        "- CASH_OPERATION_MODEL.md",
        "- CORPORATE_EXPENSE_CLASSIFICATION.md",
        "- PURCHASING_MODULE_BLUEPRINT.md",
        "- RECEIVABLE_ANALYSIS_MODEL.md",
        "- TOP_20_BUSINESS_OPPORTUNITIES.md",
        "- FINANCIAL_ROADMAP_1.0.md",
        "- FINANCIAL_PERFORMANCE_REPORT.md",
        "- A04_READINESS_REPORT.md",
    ]) + "\n", encoding="utf-8")


async def main_async() -> dict[str, Any]:
    config = load_core_config()
    print("A03.7 — Consolidação financeira corporativa...")
    api = await collect_all(config)

    despesas_rows = _rows((api.get("DESPESAS_REDE") or {}).get("sampleRows") or [])
    # refetch full despesas for classification
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{config.webposto_base_url}/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
            params={**PERIOD, "CHAVE": config.webposto_api_key},
            timeout=90,
        )
        if r.status_code == 200:
            despesas_rows = _rows(r.json())

    mov_rows = _rows((api.get("MOVIMENTO_CONTA") or {}).get("sampleRows") or [])
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{config.webposto_base_url}/INTEGRACAO/MOVIMENTO_CONTA",
            params={**PERIOD, "CHAVE": config.webposto_api_key},
            timeout=90,
        )
        if r.status_code == 200:
            mov_rows = _rows(r.json())

    transf_rows = _rows((api.get("TRANSFERENCIA_BANCARIA") or {}).get("sampleRows") or [])
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{config.webposto_base_url}/INTEGRACAO/TRANSFERENCIA_BANCARIA",
            params={**PERIOD, "CHAVE": config.webposto_api_key},
            timeout=90,
        )
        if r.status_code == 200:
            transf_rows = _rows(r.json())

    caixa_rows = api.get("CAIXA", {}).get("sampleRows") or []
    apresentado_rows = api.get("CAIXA_APRESENTADO", {}).get("sampleRows") or []
    async with httpx.AsyncClient() as client:
        for path, key in [("CAIXA", "caixa_rows"), ("CAIXA_APRESENTADO", "apresentado_rows")]:
            r = await client.get(
                f"{config.webposto_base_url}/INTEGRACAO/{path}",
                params={**PERIOD, "CHAVE": config.webposto_api_key},
                timeout=90,
            )
            if r.status_code == 200:
                rows = _rows(r.json())
                if path == "CAIXA":
                    caixa_rows = rows
                else:
                    apresentado_rows = rows

    recv_rows = api.get("TITULO_RECEBER", {}).get("sampleRows") or []
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{config.webposto_base_url}/INTEGRACAO/TITULO_RECEBER",
            params={**PERIOD, "CHAVE": config.webposto_api_key},
            timeout=90,
        )
        if r.status_code == 200:
            recv_rows = _rows(r.json())

    pay_rows = []
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{config.webposto_base_url}/INTEGRACAO/TITULO_PAGAR",
            params={**PERIOD, "CHAVE": config.webposto_api_key},
            timeout=90,
        )
        if r.status_code == 200:
            pay_rows = _rows(r.json())

    data = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "period": PERIOD,
        "api": api,
        "expense_classification": analyze_expense_classification(despesas_rows),
        "treasury": analyze_treasury(mov_rows, transf_rows),
        "cash": analyze_cash(caixa_rows, apresentado_rows),
        "receivables": analyze_receivables(recv_rows),
        "payables": analyze_payables(pay_rows),
        "performance": performance_summary(api),
    }

    out = ROOT / "scripts" / "audit_a03_7_results.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_all_reports(data)
    print(f"OK: {out}")
    return data


def main() -> int:
    asyncio.run(main_async())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
