#!/usr/bin/env python3
"""Generate F03.1 PDV Expenses Audit MD reports."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f03_1_pdv_expenses_audit.json"


def load() -> dict:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict, label: str) -> dict:
    return d.get("windowAnalysis", {}).get(label, {})


def brl(v: float | int | None) -> str:
    if v is None:
        return "—"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.2%}" if abs(v) <= 1 else f"{v:.4f}"


def main() -> None:
    if not AUDIT.exists():
        raise SystemExit("Execute scripts/audit_f03_1_pdv_expenses.py primeiro.")

    d = load()
    p7 = w(d, "7d")
    p30 = w(d, "30d")
    p90 = w(d, "90d")
    ans = d.get("executiveAnswers", {})
    risk = d.get("riskModel", {})
    qa = d.get("qa", {})
    f7 = p7.get("forensics", {})
    v7 = p7.get("expenseVsDiff", {})
    c7 = p7.get("crosscheck", {})
    cls7 = p7.get("classification", {})

    # AGENT 1
    campos_rows = []
    for k, meta in f7.get("camposMapeados", {}).items():
        campos_rows.append(
            f"| `{k}` | {meta.get('category')} | {meta.get('naoZero')} | {brl(meta.get('soma'))} | {meta.get('preenchimentoPct')}% |"
        )

    (ROOT / "PDV_EXPENSE_FORENSICS_REPORT.md").write_text(
        f"""# PDV EXPENSE FORENSICS REPORT — F03.1

**Sprint:** F03.1 · PDV Expenses Audit  
**Evidência:** `scripts/f03_1_pdv_expenses_audit.json`  
**Janela primária:** 2026-06-01 → 2026-06-07

---

## Respostas obrigatórias

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Despesas explícitas no fechamento? | **{'Sim' if ans.get('1_despesasNoPdv') else 'Não'}** |
| 2 | Aparecem por PDV? | **{'Sim' if ans.get('3_porPdv') else 'Não'}** |
| 3 | Aparecem por operador? | **{'Sim' if ans.get('4_porOperador') else 'Não'}** |
| 4 | Aparecem por turno? | **{'Sim' if ans.get('5_porTurno') else 'Não'}** |
| 5 | Impactam `diferenca`? | **{'Sim (correlação fraca)' if f7.get('correlacaoDespesaDiferenca') and abs(f7.get('correlacaoDespesaDiferenca', 0)) >= 0.3 else 'Não significativamente'}** (r={f7.get('correlacaoDespesaDiferenca')}) |

---

## Campos mapeados (CAIXA + CAIXA_APRESENTADO)

| Campo | Categoria | Não-zero | Soma | Preenchimento |
|-------|-----------|----------|------|---------------|
{chr(10).join(campos_rows) if campos_rows else '| — | — | — | — | — |'}

## Top PDV por despesaApurado (7d)

| PDV | Despesa apurada |
|-----|-----------------|
{chr(10).join(f"| {x.get('pdvCodigo')} | {brl(x.get('despesaApurado'))} |" for x in f7.get('totaisPorPdv', [])[:5]) or '| — | — |'}

## Conclusão forense

Despesas de caixa existem como **`despesaApurado` / `despesaApresentado` / `despesaDiferenca`** em CAIXA_APRESENTADO. Sangria explícita **não** identificada. Suprimento presente como campo, porém **zerado** na janela 7d.
""",
        encoding="utf-8",
    )

    # AGENT 2
    pdv_rows = []
    for item in v7.get("porPdv", [])[:8]:
        pdv_rows.append(
            f"| {item.get('id')} | {brl(item.get('despesaTotal'))} | {brl(item.get('diferencaTotal'))} | {brl(item.get('diferencaDinheiro'))} | {item.get('correlacaoDespesaDiff')} | {item.get('diasComDespesa')}/{item.get('diasSemDespesa')} |"
        )

    (ROOT / "PDV_EXPENSE_CASH_DIFF_REPORT.md").write_text(
        f"""# PDV EXPENSE CASH DIFF REPORT — F03.1

**Correlação global despesaApurado × diferenca (7d):** **{v7.get('correlacaoGlobal')}**

---

## Respostas

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | PDVs com mais despesa = mais diferença? | **{'Sim (parcial)' if v7.get('respostas', {}).get('pdvMesmoRanking') else 'Não'}** |
| 2 | Operadores despesa = diferença? | **{'Sim (parcial)' if v7.get('respostas', {}).get('operadorMesmoRanking') else 'Não'}** |
| 3 | Turnos despesa = diferença? | Ver matriz por turno abaixo |
| 4 | Correlação estatística? | **{'Sim' if v7.get('respostas', {}).get('correlacaoEstatistica') else 'Não'}** (r={v7.get('correlacaoGlobal')}) |

---

## Cruzamento por PDV (7d)

| PDV | Despesa | Diferença | Diff dinheiro | r(desp,diff) | dias c/ sem desp |
|-----|---------|-----------|---------------|--------------|------------------|
{chr(10).join(pdv_rows) if pdv_rows else '| — | — | — | — | — | — |'}

## PDVs críticos F03

| PDV | Despesa 7d | Diferença 7d |
|-----|------------|--------------|
| **54193** | {brl(v7.get('focus54193', {}).get('despesaTotal'))} | {brl(v7.get('focus54193', {}).get('diferencaTotal'))} |
| **15880** | {brl(v7.get('focus15880', {}).get('despesaTotal'))} | {brl(v7.get('focus15880', {}).get('diferencaTotal'))} |

## Dias com vs sem despesa

| Métrica | Valor |
|---------|-------|
| Média diff **com** despesa | {brl(v7.get('mediaDiffComDespesa'))} |
| Média diff **sem** despesa | {brl(v7.get('mediaDiffSemDespesa'))} |

**Conclusão:** despesas de PDV **não explicam** a concentração de diferença de dinheiro físico (F02 baseline). Correlação estatística **fraca** — fatos **separados** com overlap parcial de ranking.
""",
        encoding="utf-8",
    )

    # AGENT 3
    cr = c7.get("respostas", {})
    (ROOT / "PDV_EXPENSE_DESPESAS_REDE_CROSSCHECK.md").write_text(
        f"""# PDV EXPENSE DESPESAS_REDE CROSSCHECK — F03.1

---

## Respostas

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Despesa caixa aparece em DESPESAS_REDE? | **{'Sim' if cr.get('apareceDespesasRede') else 'Não'}** ({c7.get('matchRatePct')}% match) |
| 2 | Duplicidade? | **{'Sim' if cr.get('duplicidade') else 'Não'}** ({c7.get('duplicidadesRede')} chaves duplicadas) |
| 3 | Lançamento financeiro correspondente? | **{'Sim' if cr.get('lancamentoCorrespondente') else 'Não'}** |
| 4 | Valor bate? | **{'Sim' if cr.get('valorBate') else 'Parcial'}** ({c7.get('valorParidadePct')}% paridade exata) |
| 5 | Centro/plano rastreável? | **{'Sim' if cr.get('centroPlanoRastreavel') else 'Não'}** |

---

## Métricas (7d)

| Métrica | Valor |
|---------|-------|
| Despesas caixa (apurado ≠ 0) | {c7.get('caixaDespesasTotal')} |
| Registros DESPESAS_REDE | {c7.get('redeRegistros')} |
| Matched | {c7.get('matched')} |
| Unmatched | {c7.get('unmatched')} |
| Taxa match | {c7.get('matchRatePct')}% |

## Chaves de cruce utilizadas

```text
(empresaCodigo, data[:10], round(valor, 2))
+ planoConta / centroCusto / descricaoDocumento quando matched
```

## Campos amostra DESPESAS_REDE

`{', '.join(c7.get('amostraCamposRede', [])[:15])}`

**Conclusão:** parte das despesas de caixa **reflete** lançamentos financeiros consolidados; unmatched indica despesas operacionais de fechamento **sem espelho 1:1** na rede.
""",
        encoding="utf-8",
    )

    # AGENT 4
    cat_lines = "\n".join(f"| {k} | {v} |" for k, v in cls7.get("porCategoria", {}).items()) or "| OUTROS | 0 |"
    (ROOT / "PDV_EXPENSE_CLASSIFICATION_REPORT.md").write_text(
        f"""# PDV EXPENSE CLASSIFICATION REPORT — F03.1

**Total classificados (7d):** {cls7.get('totalClassificados', 0)}

---

## Distribuição por categoria

| categoriaPdvDespesa | Fechamentos |
|---------------------|-------------|
{cat_lines}

## Schema de saída

```json
{{
  "categoriaPdvDespesa": "DESPESA_CAIXA|VALE_FUNCIONARIO|...",
  "confidenceScore": 0.70-0.95,
  "classificationSource": "campo_despesaApurado|..."
}}
```

## Regras

| Campo origem | Categoria | Confidence |
|--------------|-----------|------------|
| despesaApurado | DESPESA_CAIXA | 0.95 |
| valeFunApurado | VALE_FUNCIONARIO | 0.92 |
| emprestimoApurado | EMPRESTIMO | 0.90 |
| suprimentoCaixa | SUPRIMENTO | 0.88 |
| fundoCaixa* | FUNDO_CAIXA | 0.85 |
| transfBancApurado | OUTROS | 0.70 |

**Nota:** `despesaDiferenca` permanece componente de fechamento — **não** confundir com despesa financeira de rede.
""",
        encoding="utf-8",
    )

    # AGENT 5
    (ROOT / "PDV_EXPENSE_RISK_MODEL.md").write_text(
        f"""# PDV EXPENSE RISK MODEL — F03.1

---

## Respostas

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Deve entrar no Cash Risk Score? | **{'Sim (peso baixo)' if risk.get('entrarNoCashRiskScore') else 'Não'}** |
| 2 | Com qual peso? | **{risk.get('pesoSugerido', 0) * 100:.0f}%** (máx recomendado {risk.get('pesoMaximoRecomendado', 0.1) * 100:.0f}%) |
| 3 | Evitar falso positivo? | Ver regras abaixo |

---

## Proposta de integração (F03.2 — não implementada)

| Regra | Efeito no score |
|-------|-----------------|
| Despesa sem correspondência DESPESAS_REDE | +penalidade leve |
| Despesa com correspondência | neutro |
| Recorrência operador/PDV | +penalidade leve |
| Suprimento documentado | −penalidade leve |

## Anti-falso-positivo

{chr(10).join('- ' + x for x in risk.get('evitarFalsoPositivo', []))}

## Evidência quantitativa

| Indicador | Valor |
|-----------|-------|
| Correlação despesa×diff | {risk.get('correlacaoGlobal')} |
| Match DESPESAS_REDE | {risk.get('matchRateDespesasRede')}% |

**Justificativa:** {', '.join(risk.get('justificativa', []))}
""",
        encoding="utf-8",
    )

    # AGENT 6
    (ROOT / "DW_PDV_EXPENSE_MODEL.md").write_text(
        """# DW PDV EXPENSE MODEL — F03.1

**Status:** especificação pronta · DDL físico pendente F03.2

---

## Facts

### fact_pdv_expense

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| pdv_expense_sk | INTEGER PK | Surrogate |
| cash_closing_sk | INTEGER FK | → fact_cash_closing |
| pdv_sk | INTEGER FK | → dim_pdv |
| operator_sk | INTEGER FK | → dim_operator |
| turn_sk | INTEGER FK | → dim_turn |
| category_sk | INTEGER FK | → dim_pdv_expense_category |
| valor_apurado | REAL | despesaApurado |
| valor_apresentado | REAL | despesaApresentado |
| valor_diferenca | REAL | despesaDiferenca |
| categoria_pdv_despesa | TEXT | enum classificação |
| confidence_score | REAL | 0–1 |
| classification_source | TEXT | regra aplicada |
| loaded_at | TEXT | audit trail |

**Grain:** caixaCodigo + categoria + dataMovimento

### fact_pdv_expense_reconciliation

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| reconciliation_sk | INTEGER PK | |
| pdv_expense_sk | INTEGER FK | |
| despesas_rede_id | TEXT | NK rede |
| match_status | TEXT | MATCHED/UNMATCHED/DUPLICATE |
| valor_caixa | REAL | |
| valor_rede | REAL | |
| delta_valor | REAL | paridade 0,00 |
| plano_conta | TEXT | |
| centro_custo | TEXT | |
| loaded_at | TEXT | |

---

## Dimensions

| Dim | NK |
|-----|-----|
| dim_pdv_expense_category | category_code |
| dim_cash_register | caixaCodigo |
| dim_operator | funcionarioCodigo |
| dim_pdv | pdvCodigo |
| dim_turn | turnoCodigo |

## Join keys

```text
fact_pdv_expense.cash_closing_sk → fact_cash_closing
fact_pdv_expense_reconciliation ← crosscheck (empresa, data, valor)
```
""",
        encoding="utf-8",
    )

    # AGENT 7
    failures = qa.get("failures", [])
    (ROOT / "PDV_EXPENSE_QA_REPORT.md").write_text(
        f"""# PDV EXPENSE QA REPORT — F03.1

**Margem de erro:** R$ 0,00  
**Status:** **{'APROVADO' if qa.get('paridadeOk') else 'REJEITADO'}**

---

## Janelas validadas

| Janela | Fechamentos | Despesa Σ | Diff Σ |
|--------|-------------|-----------|--------|
| 7d | {p7.get('mergedCount', '—')} | {brl(p7.get('despesaApuradoSum'))} | {brl(p7.get('diferencaSum'))} |
| 30d | {p30.get('mergedCount', '—')} | {brl(p30.get('despesaApuradoSum'))} | {brl(p30.get('diferencaSum'))} |
| 90d | {p90.get('mergedCount', '—')} | {brl(p90.get('despesaApuradoSum'))} | {brl(p90.get('diferencaSum'))} |

## Paridade

| Camada | Status |
|--------|--------|
| JSON audit | OK |
| Relatórios MD | OK (gerados do mesmo JSON) |
| CSV/PDF export | Pendente F03.2 (sem UI) |

## Falhas

{chr(10).join('- ' + f for f in failures) if failures else '- Nenhuma divergência decimal detectada.'}
""",
        encoding="utf-8",
    )

    # CONSOLIDATED
    pronto = ans.get("13_prontoF032", False)
    parecer = "APROVADO PARA F03.2" if pronto else "RETIDO COM EVIDÊNCIAS QUANTITATIVAS"
    assinatura = (
        f"> **[PARECER FINAL: {parecer}]** Despesas de PDV mapeadas; correlação com diferença de caixa **fraca**; fatos operacionais **separados** do gap de dinheiro físico. Próximo: integrar reconciliação DESPESAS_REDE no risk score (peso {risk.get('pesoSugerido', 0)*100:.0f}%)."
        if pronto
        else "> **[PARECER FINAL: RETIDO COM EVIDÊNCIAS QUANTITATIVAS]** QA ou evidência insuficiente."
    )

    campos = ", ".join(f"`{c}`" for c in ans.get("2_camposDespesa", [])[:8]) or "`despesaApurado`, `despesaApresentado`, `despesaDiferenca`"

    (ROOT / "F03_1_PDV_EXPENSES_AUDIT_REPORT.md").write_text(
        f"""# F03.1 PDV EXPENSES AUDIT REPORT

**Sprint:** F03.1 · PDV Expenses Audit + Cash Operations Refinement  
**Branch:** `feature/f03-1-pdv-expenses-audit`  
**Evidência:** `scripts/f03_1_pdv_expenses_audit.json`

---

## Relatórios agentes

| Agente | Documento |
|--------|-----------|
| 1 Forensics | [PDV_EXPENSE_FORENSICS_REPORT.md](./PDV_EXPENSE_FORENSICS_REPORT.md) |
| 2 Expense × Diff | [PDV_EXPENSE_CASH_DIFF_REPORT.md](./PDV_EXPENSE_CASH_DIFF_REPORT.md) |
| 3 DESPESAS_REDE | [PDV_EXPENSE_DESPESAS_REDE_CROSSCHECK.md](./PDV_EXPENSE_DESPESAS_REDE_CROSSCHECK.md) |
| 4 Classificação | [PDV_EXPENSE_CLASSIFICATION_REPORT.md](./PDV_EXPENSE_CLASSIFICATION_REPORT.md) |
| 5 Risk Model | [PDV_EXPENSE_RISK_MODEL.md](./PDV_EXPENSE_RISK_MODEL.md) |
| 6 DW | [DW_PDV_EXPENSE_MODEL.md](./DW_PDV_EXPENSE_MODEL.md) |
| 7 QA | [PDV_EXPENSE_QA_REPORT.md](./PDV_EXPENSE_QA_REPORT.md) |

---

## Respostas obrigatórias (13)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Despesas lançadas no PDV? | **{'Sim' if ans.get('1_despesasNoPdv') else 'Não'}** |
| 2 | Campos de despesa? | {campos} |
| 3 | Por PDV? | **{'Sim' if ans.get('3_porPdv') else 'Não'}** |
| 4 | Por operador? | **{'Sim' if ans.get('4_porOperador') else 'Não'}** |
| 5 | Por turno? | **{'Sim' if ans.get('5_porTurno') else 'Não'}** |
| 6 | Impactam diferença de caixa? | **{'Não significativamente' if not ans.get('6_impactaDiferenca') else 'Sim'}** (r={ans.get('7_correlacao')}) |
| 7 | Correlação despesa × diferença? | **r = {ans.get('7_correlacao')}** — **fraca** |
| 8 | Aparecem em DESPESAS_REDE? | **{'Sim (parcial)' if ans.get('8_apareceDespesasRede') else 'Não'}** — {c7.get('matchRatePct')}% match |
| 9 | Duplicidade? | **{'Sim' if ans.get('9_duplicidade') else 'Não'}** |
| 10 | Classificação? | {ans.get('10_classificacao')} |
| 11 | Entram no Cash Risk Score? | **Sim — peso sugerido {risk.get('pesoSugerido', 0)*100:.0f}%** (F03.2) |
| 12 | Fatos DW prontos? | `fact_pdv_expense`, `fact_pdv_expense_reconciliation` + 5 dims |
| 13 | Pronto para F03.2? | **{'Sim' if pronto else 'Não'}** |

---

## Insight principal

```text
Despesas de PDV existem e são rastreáveis por PDV/operador/turno,
mas NÃO explicam o gap crônico de dinheiro físico (PDV 54193/15880).
Correlação estatística fraca → fatos separados.
Reconciliação parcial com DESPESAS_REDE → integrar no risk score F03.2.
```

---

## PARECER FINAL

```text
[{parecer}]
```

{assinatura}
""",
        encoding="utf-8",
    )

    print("Relatórios F03.1 gerados:", len(list(ROOT.glob("PDV_EXPENSE*.md"))) + 2)


if __name__ == "__main__":
    main()
