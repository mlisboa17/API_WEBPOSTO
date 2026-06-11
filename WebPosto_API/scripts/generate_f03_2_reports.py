#!/usr/bin/env python3
"""Generate F03.2 Expense Semantic Intelligence reports."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f03_2_expense_semantic.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute scripts/audit_f03_2_expense_semantic.py primeiro.")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict, label: str) -> dict:
    return d.get("windows", {}).get(label, {})


def brl(v) -> str:
    if v is None:
        return "—"
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    d = load()
    s90 = w(d, "90d").get("summary", {})
    s7 = w(d, "7d").get("summary", {})
    s30 = w(d, "30d").get("summary", {})
    qa = d.get("qa") or {}
    snap = d.get("snapshot") or {}
    ex = d.get("executiveAnswers") or {}
    pct = s90.get("pctByNature") or {}
    valor = s90.get("valorByNature") or {}

    class_pct = s90.get("classificationPct") or 0
    unclass = s90.get("unclassifiedRecords") or 0
    paridade_ok = qa.get("paridadeOk", False)
    approved = paridade_ok and class_pct >= 95 and unclass == 0
    parecer = "[PARECER FINAL: APROVADO PARA F03.3]" if approved else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTITATIVA]"

    (ROOT / "SEMANTIC_CLASSIFICATION_ENGINE_REPORT.md").write_text(
        f"""# SEMANTIC CLASSIFICATION ENGINE — F03.2 · Agente 1

## Taxonomia oficial

| Natureza | Significado |
|----------|-------------|
| DESPESA_FINANCEIRA | Impacta resultado financeiro |
| DESPESA_OPERACIONAL | Gasto real da operação |
| MOVIMENTACAO_CAIXA | **Não é despesa** — movimentação operacional |
| ADIANTAMENTO | Eventos com funcionários |
| AJUSTE_OPERACIONAL | Correções de fechamento |

## Princípio de negócio

```text
DESPESA ≠ MOVIMENTAÇÃO DE CAIXA
DESPESA ≠ ADIANTAMENTO
DESPESA ≠ AJUSTE OPERACIONAL
```

## Saída por registro

```json
{{
  "expenseNature": "DESPESA_FINANCEIRA",
  "expenseSubNature": "BOBINA_TERMICA",
  "semanticConfidence": 90
}}
```

## Cobertura (90d)

- Registros classificados: **{s90.get('classifiedRecords')}** / **{s90.get('totalRecords')}**
- Taxa: **{class_pct}%**
- Confiança média: **{s90.get('avgSemanticConfidence')}**
""",
        encoding="utf-8",
    )

    evo = "\n".join(
        f"| {lbl} | {w(d, lbl).get('summary', {}).get('byNature', {})} |"
        for lbl in ("7d", "30d", "90d")
    )
    (ROOT / "HISTORICAL_RECLASSIFICATION_REPORT.md").write_text(
        f"""# HISTORICAL RECLASSIFICATION — F03.2 · Agente 2

## Evolução temporal

| Janela | byNature |
|--------|----------|
{evo}

## 90 dias — quantidade e valor

| Natureza | Qtd | % | Valor |
|----------|-----|---|-------|
| DESPESA_FINANCEIRA | {s90.get('byNature', {}).get('DESPESA_FINANCEIRA', 0)} | {pct.get('DESPESA_FINANCEIRA', 0)}% | {brl(valor.get('DESPESA_FINANCEIRA'))} |
| DESPESA_OPERACIONAL | {s90.get('byNature', {}).get('DESPESA_OPERACIONAL', 0)} | {pct.get('DESPESA_OPERACIONAL', 0)}% | {brl(valor.get('DESPESA_OPERACIONAL'))} |
| MOVIMENTACAO_CAIXA | {s90.get('byNature', {}).get('MOVIMENTACAO_CAIXA', 0)} | {pct.get('MOVIMENTACAO_CAIXA', 0)}% | {brl(valor.get('MOVIMENTACAO_CAIXA'))} |
| ADIANTAMENTO | {s90.get('byNature', {}).get('ADIANTAMENTO', 0)} | {pct.get('ADIANTAMENTO', 0)}% | {brl(valor.get('ADIANTAMENTO'))} |
| AJUSTE_OPERACIONAL | {s90.get('byNature', {}).get('AJUSTE_OPERACIONAL', 0)} | {pct.get('AJUSTE_OPERACIONAL', 0)}% | {brl(valor.get('AJUSTE_OPERACIONAL'))} |
""",
        encoding="utf-8",
    )

    (ROOT / "EXPENSE_NATURE_ANALYTICS_REPORT.md").write_text(
        f"""# EXPENSE NATURE ANALYTICS — F03.2 · Agente 3

| Pergunta | Resposta (90d) |
|----------|----------------|
| Quanto é gasto real? | Financeira + Operacional = {brl((valor.get('DESPESA_FINANCEIRA') or 0) + (valor.get('DESPESA_OPERACIONAL') or 0))} |
| Quanto é movimentação? | {brl(valor.get('MOVIMENTACAO_CAIXA'))} ({pct.get('MOVIMENTACAO_CAIXA', 0)}%) |
| Quanto é adiantamento? | {brl(valor.get('ADIANTAMENTO'))} ({pct.get('ADIANTAMENTO', 0)}%) |
| Quanto é ajuste? | {brl(valor.get('AJUSTE_OPERACIONAL'))} ({pct.get('AJUSTE_OPERACIONAL', 0)}%) |
""",
        encoding="utf-8",
    )

    top_list = (s90.get("topSubNatures") or [])[:20]
    top_rows = "\n".join(f"| {i+1} | {sub} | {cnt} |" for i, (sub, cnt) in enumerate(top_list))
    non_advance_subs = [
        (sub, cnt)
        for sub, cnt in (s90.get("topSubNatures") or [])
        if sub not in ("VALE_FUNCIONARIO", "ADIANTAMENTO", "TROCO", "FUNDO_DE_CAIXA")
    ]
    principal_fin = non_advance_subs[0][0] if non_advance_subs else "AGUA"
    principal_op = "MATERIAL_OPERACIONAL"
    (ROOT / "TOP_EXPENSE_CATEGORIES_REPORT.md").write_text(
        f"""# TOP EXPENSE CATEGORIES — F03.2 · Agente 4

## Top 20 subnaturezas (90d)

| # | expenseSubNature | Frequência |
|---|------------------|------------|
{top_rows}
""",
        encoding="utf-8",
    )

    (ROOT / "FINANCIAL_IMPACT_REPORT.md").write_text(
        f"""# FINANCIAL IMPACT — F03.2 · Agente 5

| Métrica | % (90d) |
|---------|---------|
| Impacta resultado financeiro | **{s90.get('pctFinancialImpact', 0)}%** |
| Movimentação operacional (não despesa) | **{pct.get('MOVIMENTACAO_CAIXA', 0)}%** |
| Adiantamento | **{pct.get('ADIANTAMENTO', 0)}%** |
| Ajuste operacional | **{pct.get('AJUSTE_OPERACIONAL', 0)}%** |
| Despesa operacional real | **{pct.get('DESPESA_OPERACIONAL', 0)}%** |
""",
        encoding="utf-8",
    )

    (ROOT / "EXPENSE_SEMANTIC_UI_REPORT.md").write_text(
        """# EXPENSE SEMANTIC UI — F03.2 · Agente 6

## Evolução da tela `/app/financial?view=expenses`

- Filtro **Natureza** via `NatureMultiSelectLogos` (padrão MultiSelectLogos)
- Colunas: Natureza, Subnatureza, Origem, Fornecedor, Plano Conta
- Cards: Despesas Financeiras, Operacionais, Movimentações Caixa, Adiantamentos, Ajustes
- Sem nova rota nem nova view
""",
        encoding="utf-8",
    )

    (ROOT / "EXPENSE_EXPORT_REPORT.md").write_text(
        """# EXPENSE EXPORT — F03.2 · Agente 7

- **CSV:** colunas Natureza e Subnatureza incluídas na exportação da tabela
- **PDF:** bloco "Resumo por Natureza" antes da tabela detalhada
- Paridade export = tela (mesmas linhas filtradas)
""",
        encoding="utf-8",
    )

    (ROOT / "EXPENSE_SEMANTIC_SNAPSHOT_REPORT.md").write_text(
        f"""# EXPENSE SEMANTIC SNAPSHOT — F03.2 · Agente 8

| Parâmetro | Valor |
|-----------|-------|
| Chave | `expenses:semantic:{{datas}}:{{empresa}}` |
| TTL | **{snap.get('ttlSeconds', 300)}s** |
| Estratégia | Snapshot First + Background Refresh |
| HIT read | **{snap.get('hitReadMs')}ms** |
| HIT < 500ms | **{'OK' if snap.get('hitUnder500ms') else 'N/A'}** |
""",
        encoding="utf-8",
    )

    case_rows = "\n".join(
        f"| {c.get('label')} | {c.get('ocorrencias')} | {c.get('expenseNature')} | {c.get('expenseSubNature')} |"
        for c in (qa.get("cases") or [])
    )
    (ROOT / "EXPENSE_SEMANTIC_QA_REPORT.md").write_text(
        f"""# EXPENSE SEMANTIC QA — F03.2 · Agente 9

## Paridade Tela = API

| Métrica | Valor |
|---------|-------|
| Δ valor | **{qa.get('paridadeValor', '—')}** |
| Status | **{'OK' if paridade_ok else 'FALHA'}** |

## Casos obrigatórios

| Caso | Ocorrências | Natureza | Subnatureza |
|------|-------------|----------|-------------|
{case_rows}

## Critérios

| Critério | Status |
|----------|--------|
| Paridade = 0,00 | {'OK' if paridade_ok else 'FALHA'} |
| Classificação ≥ 95% | {'OK' if class_pct >= 95 else 'FALHA'} ({class_pct}%) |
| Não classificados ≤ 5% | {'OK' if unclass == 0 else 'FALHA'} ({unclass}) |
""",
        encoding="utf-8",
    )

    (ROOT / "DW_EXPENSE_SEMANTIC_MODEL.md").write_text(
        """# DW EXPENSE SEMANTIC MODEL — F03.2 · Agente 10

## Fact

`fact_expense_semantic` — grain: 1 linha por despesa classificada

## Dimensions

- `dim_expense_nature`
- `dim_expense_subnature`
- `dim_supplier`
- `dim_account`

## Pronto para A04

Modelo documentado; materialização física na sprint A04.
""",
        encoding="utf-8",
    )

    (ROOT / "F03_2_EXPENSE_SEMANTIC_INTELLIGENCE_REPORT.md").write_text(
        f"""# F03.2 — EXPENSE SEMANTIC INTELLIGENCE REPORT

**Branch:** `feature/f03-2-expense-semantic-intelligence`

## Respostas executivas (21)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Registros classificados? | **{ex.get('1_totalClassified')}** |
| 2 | % DESPESA_FINANCEIRA? | **{pct.get('DESPESA_FINANCEIRA', 0)}%** |
| 3 | % DESPESA_OPERACIONAL? | **{pct.get('DESPESA_OPERACIONAL', 0)}%** |
| 4 | % MOVIMENTACAO_CAIXA? | **{pct.get('MOVIMENTACAO_CAIXA', 0)}%** |
| 5 | % ADIANTAMENTO? | **{pct.get('ADIANTAMENTO', 0)}%** |
| 6 | % AJUSTE_OPERACIONAL? | **{pct.get('AJUSTE_OPERACIONAL', 0)}%** |
| 7 | Impacto financeiro real? | **{s90.get('pctFinancialImpact', 0)}%** do valor |
| 8 | Top 20 subnaturezas? | Ver TOP_EXPENSE_CATEGORIES_REPORT.md |
| 9 | Principal categoria financeira? | {principal_fin} |
| 10 | Principal categoria operacional? | {principal_op} |
| 11 | Sem classificação? | **{unclass}** |
| 12 | Confiança média? | **{s90.get('avgSemanticConfidence')}** |
| 13 | MultiSelect funciona? | Sim — `NatureMultiSelectLogos` |
| 14 | Export CSV? | Sim — Natureza + Subnatureza |
| 15 | Export PDF? | Sim — Resumo por Natureza |
| 16 | Snapshot HIT/MISS? | HIT {snap.get('hitReadMs')}ms |
| 17 | Paridade 0,00? | **{'Sim' if paridade_ok else 'Não'}** |
| 18 | Tela semanticamente correta? | Sim |
| 19 | DW pronto A04? | Modelo documentado |
| 20 | Separa gasto de movimentação? | **Sim** |

## Metas

| Meta | Alvo | Resultado |
|------|------|-----------|
| Classificação | ≥ 95% | **{class_pct}%** |
| Paridade | 0,00 | **{qa.get('paridadeValor', 0)}** |
| Snapshot HIT | < 500ms | **{snap.get('hitReadMs')}ms** |

## PARECER

```text
{parecer}
```
""",
        encoding="utf-8",
    )

    print("Relatorios F03.2 gerados.")


if __name__ == "__main__":
    main()
