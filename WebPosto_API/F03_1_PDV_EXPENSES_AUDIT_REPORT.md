# F03.1 PDV EXPENSES AUDIT REPORT

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
| 1 | Despesas lançadas no PDV? | **Sim** |
| 2 | Campos de despesa? | `ap_despesaApresentado`, `ap_despesaApurado`, `ap_valeFunApresentado`, `ap_valeFunApurado`, `ap_transfBancApurado` |
| 3 | Por PDV? | **Sim** |
| 4 | Por operador? | **Sim** |
| 5 | Por turno? | **Sim** |
| 6 | Impactam diferença de caixa? | **Não significativamente** (r=-0.0409) |
| 7 | Correlação despesa × diferença? | **r = -0.0409** — **fraca** |
| 8 | Aparecem em DESPESAS_REDE? | **Sim (parcial)** — 15.8% match |
| 9 | Duplicidade? | **Sim** |
| 10 | Classificação? | {'DESPESA_CAIXA': 19, 'OUTROS': 1, 'VALE_FUNCIONARIO': 1} |
| 11 | Entram no Cash Risk Score? | **Sim — peso sugerido 8%** (F03.2) |
| 12 | Fatos DW prontos? | `fact_pdv_expense`, `fact_pdv_expense_reconciliation` + 5 dims |
| 13 | Pronto para F03.2? | **Sim** |

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
[APROVADO PARA F03.2]
```

> **[PARECER FINAL: APROVADO PARA F03.2]** Despesas de PDV mapeadas; correlação com diferença de caixa **fraca**; fatos operacionais **separados** do gap de dinheiro físico. Próximo: integrar reconciliação DESPESAS_REDE no risk score (peso 8%).
