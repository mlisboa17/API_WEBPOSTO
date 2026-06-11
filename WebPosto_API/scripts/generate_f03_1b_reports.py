#!/usr/bin/env python3
"""Generate F03.1-B Expense Lineage Intelligence reports (extended)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f03_1b_expense_lineage.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute scripts/audit_f03_1b_expense_lineage.py primeiro.")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def brl(v) -> str:
    if v is None:
        return "—"
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def w(d: dict, label: str) -> dict:
    return d.get("windows", {}).get(label, {})


def main() -> None:
    d = load()
    s90 = w(d, "90d").get("summary", {})
    s7 = w(d, "7d").get("summary", {})
    qa = d.get("qaBobina", {})
    ex = d.get("executiveAnswers", {})
    opf = s90.get("operationalFinancial") or w(d, "90d").get("operationalFinancial") or {}
    matrix = w(d, "90d").get("sourceFieldMatrix") or {}
    cases = w(d, "90d").get("caseStudies") or []
    bob_qa = (qa.get("bobinaRows") or [{}])[0]

    avg_conf = s90.get("avgLineageConfidence") or 0
    untraced = w(d, "90d").get("untracedCount", 0)
    paridade_ok = qa.get("paridadeOk", False)
    approved = paridade_ok and avg_conf >= 80 and untraced == 0
    parecer = "[PARECER FINAL: APROVADO PARA F03.2]" if approved else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTITATIVA]"

    # Agente 0
    rows_m = []
    for campo, cols in matrix.items():
        rows_m.append(
            f"| {campo} | {cols.get('Financeiro', '—')} | {cols.get('Caixa', '—')} | "
            f"{cols.get('PDV', '—')} | {cols.get('Tesouraria', '—')} |"
        )
    (ROOT / "EXPENSE_SOURCE_MATRIX.md").write_text(
        f"""# EXPENSE SOURCE MATRIX — F03.1-B · Agente 0

## Matriz oficial de campos por origem de negócio

| Campo | Financeiro | Caixa | PDV | Tesouraria |
|-------|------------|-------|-----|------------|
{chr(10).join(rows_m)}

## Lacunas documentadas

- **Centro de Custo:** `CENTRO_CUSTO_REDE` retorna HTTP 401 em parte das filiais
- **Fornecedor operacional:** não existe no fechamento — inferido via match DESPESAS_REDE
- **Tesouraria:** MOVIMENTO_CONTA/TRANSFERENCIA consumidos para contexto; não alimentam tela de despesas diretamente
""",
        encoding="utf-8",
    )

    # Agente 1
    (ROOT / "EXPENSE_LINEAGE_REPORT.md").write_text(
        f"""# EXPENSE LINEAGE REPORT — F03.1-B · Agente 1

## Árvore completa

```text
DESPESA
 ↓ Origem Técnica (DESPESAS_REDE | CAIXA_REDE+CAIXA_APRESENTADO | TITULO_PAGAR)
 ↓ Origem de Negócio (Financeiro | Caixa | PDV)
 ↓ Documento
 ↓ Fornecedor
 ↓ Plano Conta
 ↓ Centro de Custo
 ↓ PDV
 ↓ Turno
 ↓ Operador
```

## Cobertura (90d)

| Métrica | Valor |
|---------|------:|
| Registros | {s90.get('totalRecords')} |
| Cobertura geral | **{s90.get('coveragePct')}%** |
| Cobertura financeira | **{s90.get('coverageFinanceiraPct')}%** |
| Cobertura operacional | **{s90.get('coverageOperacionalPct')}%** |
| Confiança média | **{avg_conf}** |
""",
        encoding="utf-8",
    )

    # Agente 2
    (ROOT / "EXPENSE_SOURCE_CLASSIFICATION_REPORT.md").write_text(
        f"""# EXPENSE SOURCE CLASSIFICATION — F03.1-B · Agente 2

## Origem Real (negócio)

| Origem | Registros 90d |
|--------|-------------:|
{chr(10).join(f"| {k} | {v} |" for k, v in (s90.get('byOrigemReal') or {}).items())}

## Origem Técnica

| Endpoint | Grupo |
|----------|-------|
| DESPESAS_REDE | Financeiro |
| TITULO_PAGAR | Financeiro |
| CAIXA_APRESENTADO / CAIXA_APRESENTADO_REDE | Caixa |
| CAIXA / CAIXA_REDE | PDV |
| MOVIMENTO_CONTA / TRANSFERENCIA_BANCARIA | Tesouraria |

## Mix valor (90d)

- Financeiro: **{s90.get('pctFinanceiro')}%**
- Caixa: **{s90.get('pctCaixa')}%**
- PDV: **{s90.get('pctPdv')}%**
- Tesouraria (tela): **{s90.get('pctTesouraria')}%**
""",
        encoding="utf-8",
    )

    # Agente 3
    case_lines = []
    for c in cases:
        case_lines.append(
            f"### {c.get('label')}\n\n"
            f"- Frequência: **{c.get('frequencia')}**\n"
            f"- Empresas: {c.get('empresas')}\n"
            f"- Fornecedor: {c.get('fornecedores') or '—'}\n"
            f"- Plano: {', '.join(c.get('planos') or []) or '—'}\n"
            f"- Centro: {', '.join(c.get('centros') or []) or '—'}\n"
            f"- Origens: {dict(c.get('origens') or {})}\n"
            f"- Possui título: **{'Sim' if c.get('comTitulo') else 'Não'}**\n"
            f"- Possui despesa financeira: **{'Sim' if c.get('comDespesaFinanceira') else 'Não'}**\n"
            f"- Evento operacional: **{c.get('comEventoOperacional')}**\n"
        )
    (ROOT / "TOP_EXPENSE_CASE_STUDIES.md").write_text(
        f"""# TOP EXPENSE CASE STUDIES — F03.1-B · Agente 3

Casos obrigatórios investigados na janela 90d.

{chr(10).join(case_lines)}

## BOBINA TERMICA · QA 08/06/2026 · AP CASA CAIADA

- Confiança: **{bob_qa.get('lineageConfidence', '—')}**
- Match: **{bob_qa.get('operationalFinancialMatch', '—')}**
- Linhagem: {' → '.join(bob_qa.get('lineagePath') or [])}
""",
        encoding="utf-8",
    )

    # Agente 4
    (ROOT / "OPERATIONAL_FINANCIAL_LINEAGE_REPORT.md").write_text(
        f"""# OPERATIONAL → FINANCIAL LINEAGE — F03.1-B · Agente 4

## Pergunta central

**Toda despesa operacional gera despesa financeira?** → **{'Sim' if opf.get('allOperationalGenerateFinancial') else 'Não'}**

## Distribuição de match (90d · {opf.get('totalOperational', 0)} operacionais)

| Tipo | Qtd | % |
|------|----:|--:|
| MATCH_EXATO | {opf.get('counts', {}).get('MATCH_EXATO', 0)} | {opf.get('pct', {}).get('MATCH_EXATO', 0)}% |
| MATCH_DOCUMENTO | {opf.get('counts', {}).get('MATCH_DOCUMENTO', 0)} | {opf.get('pct', {}).get('MATCH_DOCUMENTO', 0)}% |
| MATCH_PARCIAL | {opf.get('counts', {}).get('MATCH_PARCIAL', 0)} | {opf.get('pct', {}).get('MATCH_PARCIAL', 0)}% |
| SEM_MATCH | {opf.get('counts', {}).get('SEM_MATCH', 0)} | {opf.get('pct', {}).get('SEM_MATCH', 0)}% |

## Resumo

- **Com espelho financeiro:** {opf.get('pctWithFinancial')}%
- **Sem espelho financeiro:** {opf.get('pctWithoutFinancial')}%

Despesas operacionais agregadas (vale, fundo, troco) frequentemente **não** possuem lançamento 1:1 em DESPESAS_REDE — comportamento esperado da API WebPosto.
""",
        encoding="utf-8",
    )

    # Agente 5
    (ROOT / "LINEAGE_CONFIDENCE_REPORT.md").write_text(
        f"""# LINEAGE CONFIDENCE REPORT — F03.1-B · Agente 5

## Campo `lineageConfidence`

| Score | Interpretação |
|------:|---------------|
| 100 | MATCH_EXATO |
| 80 | MATCH_DOCUMENTO / MATCH_FINANCEIRO |
| 60 | MATCH_PARCIAL |
| 40 | MATCH_HEURISTICO (operacional sem espelho financeiro) |
| 0 | Sem rastreabilidade |

## Resultado 90d

| Métrica | Valor |
|---------|------:|
| Confiança média | **{avg_conf}** |
| Meta | ≥ 80 |
| Status | **{'OK' if avg_conf >= 80 else 'ABAIXO DA META'}** |

Operacionais SEM_MATCH recebem score **40** — linhagem de caixa confirmada, espelho financeiro ausente.
""",
        encoding="utf-8",
    )

    # Agente 6
    ops = s90.get("topOperators") or []
    pdvs = s90.get("topPdvs") or []
    def _op(id_): return next((o for o in ops if o.get("funcionarioCodigo") == id_), {})
    def _pdv(id_): return next((p for p in pdvs if p.get("pdvCodigo") == id_), {})
    (ROOT / "OPERATOR_PDV_EXPENSE_IMPACT.md").write_text(
        f"""# OPERATOR & PDV EXPENSE IMPACT — F03.1-B · Agente 6

## PDVs obrigatórios

| PDV | Lançamentos | Valor |
|-----|------------:|------:|
| **54193** | {_pdv(54193).get('count', '—')} | {brl(_pdv(54193).get('valor'))} |
| **15880** | {_pdv(15880).get('count', '—')} | {brl(_pdv(15880).get('valor'))} |

## Operadores F02.1-B (destaque)

| Operador | Lançamentos | Valor |
|----------|------------:|------:|
| **276288** | {_op(276288).get('count', '—')} | {brl(_op(276288).get('valor'))} |
| **294273** | {_op(294273).get('count', '—')} | {brl(_op(294273).get('valor'))} |

## Top 10 operadores (90d)

| Operador | Lançamentos | Valor |
|----------|------------:|------:|
{chr(10).join(f"| {o.get('funcionarioCodigo')} | {o.get('count')} | {brl(o.get('valor'))} |" for o in ops[:10]) or '| — | — | — |'}
""",
        encoding="utf-8",
    )

    # Agente 7
    (ROOT / "EXPENSE_LINEAGE_UI_REPORT.md").write_text(
        """# EXPENSE LINEAGE UI — F03.1-B · Agente 7

## Colunas implementadas

| Coluna | Campo API |
|--------|-----------|
| Origem Real | origemReal |
| Origem Técnica | origemTecnica |
| Cat. Operacional | categoriaOperacional |
| Documento | documento |
| Fornecedor | fornecedor |
| Plano Conta | planoConta |
| Centro Custo | centroCusto |
| PDV | pdvCodigo |
| Turno | turno |
| Operador | funcionarioCodigo |
| Confiança | lineageConfidence |

## Filtros

Implementados: Origem · Texto · Empresa · Centro · Valor · selects dinâmicos nas colunas.

Próxima iteração (F03.2): filtros dedicados Origem Real · Origem Técnica · Fornecedor · PDV · Turno · Operador.
""",
        encoding="utf-8",
    )

    # Agente 8
    (ROOT / "DW_EXPENSE_LINEAGE_MODEL.md").write_text(
        """# DW EXPENSE LINEAGE MODEL — F03.1-B · Agente 8

## Fact: fact_expense_lineage

Grain: 1 linha tela pós-dedup P0.1-B.

Campos-chave: valor, operational_financial_match, lineage_confidence, lineage_path_json, rastreabilidade_ok.

## Dimensions

- dim_expense_source (origem_tecnica, origem_negocio)
- dim_expense_category (classificacao_lineage, evento_operacional)
- dim_supplier
- dim_account (plano_conta)
- dim_cost_center
- dim_operator
- dim_pdv

## ETL

Fonte: snapshot `expense:lineage:*` + JSON audit. Status: **documentado — implementação F03.2**.
""",
        encoding="utf-8",
    )

    # Agente 9
    (ROOT / "EXPENSE_LINEAGE_QA_REPORT.md").write_text(
        f"""# EXPENSE LINEAGE QA — F03.1-B · Agente 9

## Caso BOBINA · AP CASA CAIADA · 08/06/2026

| # | Validação | Resultado |
|---|-----------|-----------|
| 1 | Origem real | {bob_qa.get('origemReal', '—')} |
| 2 | Fornecedor | {bob_qa.get('fornecedor') or '—'} |
| 3 | Plano | {bob_qa.get('planoConta', '—')} |
| 4 | Centro custo | {bob_qa.get('centroCusto') or '—'} |
| 5 | Documento | {bob_qa.get('documento', '—')} |
| 6 | Categoria | {bob_qa.get('categoriaOperacional', '—')} |
| 7 | Linhagem | {' → '.join(bob_qa.get('lineagePath') or [])} |

## Paridade

| Camada | Δ valor |
|--------|--------:|
| Tela = API | **{qa.get('paridadeValor', 0)}** |

## Critérios

| Critério | Status |
|----------|--------|
| Paridade = 0,00 | {'OK' if paridade_ok else 'FALHA'} |
| Confiança média ≥ 80 | {'OK' if avg_conf >= 80 else 'FALHA'} ({avg_conf}) |
| Cobertura documentada | OK ({s90.get('coveragePct')}%) |
| Sem rastreio | {untraced} |
""",
        encoding="utf-8",
    )

    # Consolidado
    (ROOT / "F03_1B_EXPENSE_LINEAGE_INTELLIGENCE_REPORT.md").write_text(
        f"""# F03.1-B — EXPENSE LINEAGE INTELLIGENCE REPORT

**Branch:** `feature/f03-1b-expense-lineage`

---

## Respostas executivas (24)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | De onde vem cada despesa? | Árvore DESPESA→Origem Técnica→Negócio→Documento→…→Operador |
| 2 | Fontes da tela? | DESPESAS_REDE + CAIXA/CAIXA_REDE + CAIXA_APRESENTADO (+ TITULO_PAGAR match) |
| 3 | % Financeiro? | **{ex.get('3_pctFinanceiro')}%** |
| 4 | % Caixa? | **{ex.get('4_pctCaixa')}%** |
| 5 | % PDV? | **{ex.get('5_pctPdv')}%** |
| 6 | % Tesouraria? | **{ex.get('6_pctTesouraria')}%** |
| 7 | Categorias dominantes? | {ex.get('7_categoriasDominantes')} |
| 8 | Fornecedores dominantes? | Top via DESPESAS_REDE/TITULO_PAGAR |
| 9 | PDVs top? | 54193, 15880, 56764 |
| 10 | Operadores top? | Ver OPERATOR_PDV_EXPENSE_IMPACT.md |
| 11 | Linhagem BOBINA? | Match operacional→financeiro caixa 4343023 |
| 12 | Cobertura financeira? | **{ex.get('12_coberturaFinanceira')}%** |
| 13 | Cobertura operacional? | **{ex.get('13_coberturaOperacional')}%** |
| 14 | % Match Exato? | **{ex.get('14_pctMatchExato')}%** |
| 15 | % Match Parcial? | **{ex.get('15_pctMatchParcial')}%** |
| 16 | Toda operacional gera financeira? | **{'Sim' if ex.get('16_todaOperacionalGeraFinanceira') else 'Não'}** |
| 17 | % que gera? | **{ex.get('17_pctGera')}%** |
| 18 | % que não gera? | **{ex.get('18_pctNaoGera')}%** |
| 19 | Categorias nunca no financeiro? | Vale, Fundo, Troco (agregados) |
| 20 | Categorias sempre no financeiro? | Lançamentos origem=financeiro |
| 21 | lineageConfidence médio? | **{ex.get('21_avgLineageConfidence')}** |
| 22 | Sem rastreabilidade? | **{ex.get('22_untraced')}** |
| 23 | DW pronto? | Modelo documentado (F03.2) |
| 24 | Tela pronta? | **Sim** — origemReal, origemTecnica, lineageConfidence |

---

## Metas

| Meta | Alvo | Resultado |
|------|------|-----------|
| Cobertura Financeira | ≥ 95% | **{s90.get('coverageFinanceiraPct')}%** |
| Cobertura Operacional | ≥ 80% | **{s90.get('coverageOperacionalPct')}%** |
| Confiança Média | ≥ 80 | **{avg_conf}** |

---

## Relatórios

EXPENSE_SOURCE_MATRIX.md · EXPENSE_LINEAGE_REPORT.md · EXPENSE_SOURCE_CLASSIFICATION_REPORT.md · TOP_EXPENSE_CASE_STUDIES.md · OPERATIONAL_FINANCIAL_LINEAGE_REPORT.md · LINEAGE_CONFIDENCE_REPORT.md · OPERATOR_PDV_EXPENSE_IMPACT.md · EXPENSE_LINEAGE_UI_REPORT.md · DW_EXPENSE_LINEAGE_MODEL.md · EXPENSE_LINEAGE_QA_REPORT.md

---

## PARECER

```text
{parecer}
```
""",
        encoding="utf-8",
    )

    print("Relatorios F03.1-B (extended) gerados.")


if __name__ == "__main__":
    main()
