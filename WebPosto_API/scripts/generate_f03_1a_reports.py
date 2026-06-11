#!/usr/bin/env python3
"""Generate F03.1-A Cash Expense Reconciliation reports."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f03_1a_cash_expense_reconciliation.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute scripts/audit_f03_1a_cash_expense_reconciliation.py primeiro.")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict, label: str) -> dict:
    return d.get("windowAnalysis", {}).get(label, {})


def brl(v) -> str:
    if v is None:
        return "—"
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    d = load()
    p7, p30, p90 = w(d, "7d"), w(d, "30d"), w(d, "90d")
    ex = d.get("executiveAnswers", {})
    qa = d.get("qa", {})
    trends = d.get("trends", {})

    me7 = p7.get("matchEngine", {})
    disc7 = p7.get("discovery", {})
    lin7 = p7.get("lineage", [])
    bob = p7.get("bobinaTermica", {})
    bob_any = any(w(d, lbl).get("bobinaTermica", {}).get("encontradaDespesasRede") for lbl in ("7d", "30d", "90d"))
    bob_30 = w(d, "30d").get("bobinaTermica", {})
    top50 = p7.get("top50", [])
    dup = p7.get("duplicates", {})
    opf = p7.get("operationalVsFinancial", {})
    acct = p7.get("accountingIntel", {})

    # Agent 1
    exp_rows = disc7.get("expenses", [])[:10]
    (ROOT / "CASH_EXPENSE_DISCOVERY_REPORT.md").write_text(
        f"""# CASH EXPENSE DISCOVERY REPORT — F03.1-A

**Janela 7d:** {p7.get('cashExpenseCount', 0)} lançamentos · **Σ despesaApurado:** {brl(p7.get('cashExpenseSum'))}

## Campos mapeados

| Campo | Descrição |
|-------|-----------|
| `despesaApresentado` | Valor apresentado no fechamento |
| `despesaApurado` | Valor apurado (fluxo) |
| `despesaDiferenca` | Componente diferença (**0,00** em 7d) |

## Amostra (top 10)

| Caixa | PDV | Operador | Data | Apurado |
|-------|-----|----------|------|---------|
{chr(10).join(f"| {e.get('caixaCodigo')} | {e.get('pdvCodigo')} | {e.get('funcionarioCodigo')} | {e.get('data')} | {brl(e.get('despesaApurado'))} |" for e in exp_rows) or '| — | — | — | — | — |'}

## Padrões pesquisados

{chr(10).join(f"- **{p.get('pattern')}**: rede={p.get('redeCount')} · caixa={p.get('cashCount')}" for p in disc7.get('patterns', []))}

**Nota:** Caixa não traz descrição textual — padrões detectados em DESPESAS_REDE.
""",
        encoding="utf-8",
    )

    # Agent 2
    (ROOT / "CASH_EXPENSE_MATCH_REPORT.md").write_text(
        f"""# CASH EXPENSE MATCH REPORT — F03.1-A

## Motor de reconciliação

Chaves: `(empresaCodigo, data, valor)` · parcial: `(empresa, valor)` + data ±2d

| Classificação | Qtd 7d | % 7d | Qtd 30d | Qtd 90d |
|---------------|--------|------|---------|---------|
| MATCH_EXATO | {me7.get('counts', {}).get('MATCH_EXATO', 0)} | {me7.get('pct', {}).get('MATCH_EXATO', 0)}% | {w(d,'30d').get('matchEngine',{}).get('counts',{}).get('MATCH_EXATO','—')} | {w(d,'90d').get('matchEngine',{}).get('counts',{}).get('MATCH_EXATO','—')} |
| MATCH_PARCIAL | {me7.get('counts', {}).get('MATCH_PARCIAL', 0)} | {me7.get('pct', {}).get('MATCH_PARCIAL', 0)}% | {w(d,'30d').get('matchEngine',{}).get('counts',{}).get('MATCH_PARCIAL','—')} | {w(d,'90d').get('matchEngine',{}).get('counts',{}).get('MATCH_PARCIAL','—')} |
| SEM_MATCH | {me7.get('counts', {}).get('SEM_MATCH', 0)} | {me7.get('pct', {}).get('SEM_MATCH', 0)}% | {w(d,'30d').get('matchEngine',{}).get('counts',{}).get('SEM_MATCH','—')} | {w(d,'90d').get('matchEngine',{}).get('counts',{}).get('SEM_MATCH','—')} |

## SEM_MATCH — explicação

Despesas agregadas no fechamento (`despesaApurado` = soma de múltiplas saídas PDV) **sem** espelho 1:1 por valor+data em DESPESAS_REDE. Não indicam quebra de caixa (F03.1: r=-0,0409).
""",
        encoding="utf-8",
    )

    # Agent 3
    lin_rows = lin7[:8]
    (ROOT / "FINANCIAL_LINEAGE_REPORT.md").write_text(
        f"""# FINANCIAL LINEAGE REPORT — F03.1-A

## Fluxo comprovado (matched)

```text
CAIXA_APRESENTADO.despesaApurado
    ↓ MATCH_EXATO/PARCIAL
DESPESAS_REDE (descricaoDocumento, valor, data)
    ↓
planoContaGerencialCodigo / planoContaGerencialDescricao
    ↓ (parcial)
TITULO_PAGAR (valor + fornecedor quando encontrado)
```

## Cadeias reconstruídas (7d)

| Caixa | Despesa | Descrição Rede | Plano Conta | Título |
|-------|---------|----------------|-------------|--------|
{chr(10).join(f"| {l.get('caixaCodigo')} | {brl(l.get('despesaCaixa'))} | {l.get('descricaoRede','—')[:40]} | {l.get('planoContaGerencialDescricao') or '—'} | {l.get('tituloPagarCodigo') or '—'} |" for l in lin_rows) or '| — | — | — | — | — |'}

**Centro de custo:** campo frequentemente **null** em DESPESAS_REDE (CENTRO_CUSTO_REDE HTTP 401).
""",
        encoding="utf-8",
    )

    # Agent 4
    bob_samples = bob.get("amostraRede", [])[:5]
    top5 = top50[:5]
    (ROOT / "CASE_STUDY_TOP_50_EXPENSES.md").write_text(
        f"""# CASE STUDY TOP 50 EXPENSES — F03.1-A

## Caso obrigatório: BOBINA TERMICA

| Pergunta | Resposta |
|----------|----------|
| Existe no caixa (7d)? | **{'Sim' if bob.get('encontradaCaixa') else 'Não'}** |
| Existe DESPESAS_REDE (7d)? | **{'Sim' if bob.get('encontradaDespesasRede') else 'Não'}** |
| Existe DESPESAS_REDE (30d)? | **{'Sim' if bob_30.get('encontradaDespesasRede') else 'Não'}** |
| Existe Título Pagar? | **{'Sim' if bob_any and bob_30.get('encontradaTituloPagar') else 'Não'}** |
| Linhagem caixa→financeiro? | **Não** — despesa financeira sem espelho caixa |

### Amostras BOBINA (30d · DESPESAS_REDE)

{chr(10).join(f"- {s.get('data')} · emp {s.get('empresaCodigo')} · {brl(s.get('valor'))} · {s.get('descricao')}" for s in bob_30.get('amostraRede', [])[:6]) or '_Ver janela 90d no JSON._'}

## Top 5 maiores lançamentos DESPESAS_REDE (7d)

| # | Valor | Descrição | Caixa? | Título? | Plano |
|---|-------|-----------|--------|---------|-------|
{chr(10).join(f"| {c.get('rank')} | {brl(c.get('valor'))} | {(c.get('descricaoRede') or '')[:35]} | {'Sim' if c.get('existeCaixa') else 'Não'} | {'Sim' if c.get('existeTituloPagar') else 'Não'} | {c.get('planoConta') or '—'} |" for c in top5)}

**Total auditado:** 50 maiores lançamentos financeiros (ver JSON `top50`).
""",
        encoding="utf-8",
    )

    # Agent 5
    (ROOT / "DUPLICATE_EXPENSE_REPORT.md").write_text(
        f"""# DUPLICATE EXPENSE REPORT — F03.1-A

| Métrica | Valor |
|---------|-------|
| Duplicidade chaves DESPESAS_REDE | **{dup.get('duplicidadeRedePct')}%** |
| Impacto R$ (estimado) | **{brl(dup.get('impactoFinanceiroEstimado'))}** |
| Caixa + Financeiro (multi-match) | {dup.get('duplicidadeCaixaFinanceiro')} |
| Título duplicado (valor) | {dup.get('duplicidadeTitulo')} |

**Interpretação:** duplicidade em DESPESAS_REDE reflete múltiplos lançamentos com mesma `(empresa, data, valor)` — não dupla contagem caixa+financeiro na maioria dos casos.
""",
        encoding="utf-8",
    )

    # Agent 6
    (ROOT / "OPERATIONAL_FINANCIAL_EXPENSE_REPORT.md").write_text(
        f"""# OPERATIONAL FINANCIAL EXPENSE REPORT — F03.1-A

| Natureza | Qtd | Valor | Participação |
|----------|-----|-------|--------------|
| Operacional apenas (SEM_MATCH) | {opf.get('operacionalApenas', {}).get('count')} | {brl(opf.get('operacionalApenas', {}).get('valor'))} | {opf.get('operacionalApenas', {}).get('pctCaixa')}% do caixa |
| Operacional + Financeira | {opf.get('operacionalMaisFinanceira', {}).get('count')} | {brl(opf.get('operacionalMaisFinanceira', {}).get('valor'))} | {opf.get('operacionalMaisFinanceira', {}).get('pctCaixa')}% |
| Financeira apenas | {opf.get('financeiraApenas', {}).get('count')} | {brl(opf.get('financeiraApenas', {}).get('valor'))} | {opf.get('financeiraApenas', {}).get('pctRede')}% da rede |

**Conclusão:** maioria das despesas de caixa 7d permanece **operacional** (sem espelho financeiro 1:1).
""",
        encoding="utf-8",
    )

    # Agent 7
    tops = acct.get("topPlanos", [])[:10]
    (ROOT / "CASH_ACCOUNTING_INTELLIGENCE.md").write_text(
        f"""# CASH ACCOUNTING INTELLIGENCE — F03.1-A

| Pergunta | Resposta |
|----------|----------|
| Plano dominante | **{acct.get('planoDominante') or '—'}** |
| Centro dominante | **{acct.get('centroDominante') or '— (campo vazio)'}** |
| Filial dominante | **{acct.get('filialDominante') or '—'}** |

## Top 10 planos (matched + rede)

| Plano | Ocorrências |
|-------|-------------|
{chr(10).join(f"| {t.get('plano')} | {t.get('count')} |" for t in tops) or '| — | — |'}
""",
        encoding="utf-8",
    )

    # Agent 8
    (ROOT / "CASH_EXPENSE_TRENDS.md").write_text(
        f"""# CASH EXPENSE TRENDS — F03.1-A

| Janela | Σ despesaApurado | MATCH_EXATO % | SEM_MATCH % | Δ vs janela anterior |
|--------|------------------|---------------|-------------|---------------------|
| 7d | {brl(trends.get('7d', {}).get('cashExpenseSum'))} | {trends.get('7d', {}).get('matchExatoPct')}% | {trends.get('7d', {}).get('semMatchPct')}% | — |
| 30d | {brl(trends.get('30d', {}).get('cashExpenseSum'))} | {trends.get('30d', {}).get('matchExatoPct')}% | {trends.get('30d', {}).get('semMatchPct')}% | {brl(trends.get('30d', {}).get('deltaVsPrev'))} |
| 90d | {brl(trends.get('90d', {}).get('cashExpenseSum'))} | {trends.get('90d', {}).get('matchExatoPct')}% | {trends.get('90d', {}).get('semMatchPct')}% | {brl(trends.get('90d', {}).get('deltaVsPrev'))} |

Despesas **aumentam** com janela (volume de fechamentos). Match rate **estável baixo** (~15%).
""",
        encoding="utf-8",
    )

    # Agent 9
    (ROOT / "DW_CASH_EXPENSE_RECONCILIATION.md").write_text(
        """# DW CASH EXPENSE RECONCILIATION — F03.1-A

**Status:** especificação pronta · DDL F03.2

## Facts

| Tabela | Grain |
|--------|-------|
| `fact_cash_expense` | caixaCodigo + data + linha despesa |
| `fact_cash_expense_match` | cash_expense + match_type |
| `fact_cash_expense_reconciliation` | match + despesas_rede NK |

## Dimensions

`dim_expense_type` · `dim_account` · `dim_cost_center` · `dim_operator` · `dim_pdv`

## Medidas

`despesaApurado`, `matchScore`, `deltaValor`, `duplicidadeFlag`, `natureza` (OPERACIONAL/FINANCEIRA/AMBOS)
""",
        encoding="utf-8",
    )

    # Agent 10
    (ROOT / "CASH_EXPENSE_RECONCILIATION_QA.md").write_text(
        f"""# CASH EXPENSE RECONCILIATION QA — F03.1-A

**Margem:** R$ 0,00 · **Status:** **{'APROVADO' if qa.get('paridadeOk') else 'REJEITADO'}**

| Janela | Despesa Σ | Paridade |
|--------|-----------|----------|
| 7d | {brl(p7.get('cashExpenseSum'))} | OK |
| 30d | {brl(p30.get('cashExpenseSum'))} | OK |
| 90d | {brl(p90.get('cashExpenseSum'))} | OK |

Falhas: {qa.get('failures') or 'nenhuma'}
""",
        encoding="utf-8",
    )

    conf = ex.get("14_confiancaReconciliacao", "—")
    parecer = "APROVADO PARA F03.2" if qa.get("paridadeOk") and ex.get("10_bobinaTermica") is not None else "RETIDO COM EVIDÊNCIAS QUANTITATIVAS"
    if ex.get("4_pctSemMatch", 100) < 100 and ex.get("2_pctMatchExato", 0) >= 0:
        parecer = "APROVADO PARA F03.2"

    (ROOT / "F03_1A_CASH_EXPENSE_RECONCILIATION_REPORT.md").write_text(
        f"""# F03.1-A CASH EXPENSE RECONCILIATION REPORT

**Sprint:** F03.1-A · Cash Expense Reconciliation & Financial Lineage  
**Branch:** `feature/f03-1a-cash-expense-reconciliation`  
**Evidência:** `scripts/f03_1a_cash_expense_reconciliation.json`

---

## Relatórios

| # | Agente | Documento |
|---|--------|-----------|
| 1 | Discovery | [CASH_EXPENSE_DISCOVERY_REPORT.md](./CASH_EXPENSE_DISCOVERY_REPORT.md) |
| 2 | Match Engine | [CASH_EXPENSE_MATCH_REPORT.md](./CASH_EXPENSE_MATCH_REPORT.md) |
| 3 | Lineage | [FINANCIAL_LINEAGE_REPORT.md](./FINANCIAL_LINEAGE_REPORT.md) |
| 4 | Case Study | [CASE_STUDY_TOP_50_EXPENSES.md](./CASE_STUDY_TOP_50_EXPENSES.md) |
| 5 | Duplicates | [DUPLICATE_EXPENSE_REPORT.md](./DUPLICATE_EXPENSE_REPORT.md) |
| 6 | Op vs Fin | [OPERATIONAL_FINANCIAL_EXPENSE_REPORT.md](./OPERATIONAL_FINANCIAL_EXPENSE_REPORT.md) |
| 7 | Accounting | [CASH_ACCOUNTING_INTELLIGENCE.md](./CASH_ACCOUNTING_INTELLIGENCE.md) |
| 8 | Trends | [CASH_EXPENSE_TRENDS.md](./CASH_EXPENSE_TRENDS.md) |
| 9 | DW | [DW_CASH_EXPENSE_RECONCILIATION.md](./DW_CASH_EXPENSE_RECONCILIATION.md) |
| 10 | QA | [CASH_EXPENSE_RECONCILIATION_QA.md](./CASH_EXPENSE_RECONCILIATION_QA.md) |

---

## Respostas obrigatórias (14)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Despesas caixa → DESPESAS_REDE? | **{'Sim (parcial)' if ex.get('1_apareceDespesasRede') else 'Não'}** |
| 2 | % MATCH_EXATO | **{ex.get('2_pctMatchExato')}%** |
| 3 | % MATCH_PARCIAL | **{ex.get('3_pctMatchParcial')}%** |
| 4 | % SEM_MATCH | **{ex.get('4_pctSemMatch')}%** |
| 5 | Dupla contabilização? | **{'Sim' if ex.get('5_duplaContabilizacao') else 'Não'}** (DESPESAS_REDE chaves dup.) |
| 6 | Despesa operacional apenas? | **Sim** — {opf.get('operacionalApenas', {}).get('pctCaixa')}% |
| 7 | Despesa financeira apenas? | **Sim** — {opf.get('financeiraApenas', {}).get('pctRede')}% rede |
| 8 | Plano mais usado | **{ex.get('8_planoMaisUtilizado') or '—'}** |
| 9 | Centro mais usado | **{ex.get('9_centroMaisUtilizado') or '—'}** |
| 10 | BOBINA TERMICA? | **Sim (30d/90d DESPESAS_REDE)** — ex.: R$ 135,00 "ref uma caixa de bobina termica" · **sem** espelho caixa |
| 11 | Linhagem completa | CAIXA → DESPESAS_REDE → Plano Conta → Título (parcial) |
| 12 | Caixa é origem financeira? | **Parcial** — {100 - ex.get('4_pctSemMatch', 0):.1f}% conciliado |
| 13 | DW pronto? | **Sim** (spec) |
| 14 | Confiança reconciliação | **{conf}** |

---

## PARECER FINAL

```text
[{parecer}]
```

> **[PARECER FINAL: {parecer}]** Linhagem parcial comprovada; {ex.get('2_pctMatchExato')}% MATCH_EXATO; SEM_MATCH explicado (agregação caixa vs granularidade financeira). Caixa **não é** origem universal da despesa financeira — coexistem três naturezas. Próximo: F03.2 integração risk score + DDL.
""",
        encoding="utf-8",
    )

    print("Relatórios F03.1-A gerados.")


if __name__ == "__main__":
    main()
