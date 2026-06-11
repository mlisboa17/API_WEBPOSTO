# PDV EXPENSE FORENSICS REPORT — F03.1

**Sprint:** F03.1 · PDV Expenses Audit  
**Evidência:** `scripts/f03_1_pdv_expenses_audit.json`  
**Janela primária:** 2026-06-01 → 2026-06-07

---

## Respostas obrigatórias

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Despesas explícitas no fechamento? | **Sim** |
| 2 | Aparecem por PDV? | **Sim** |
| 3 | Aparecem por operador? | **Sim** |
| 4 | Aparecem por turno? | **Sim** |
| 5 | Impactam `diferenca`? | **Não significativamente** (r=-0.0409) |

---

## Campos mapeados (CAIXA + CAIXA_APRESENTADO)

| Campo | Categoria | Não-zero | Soma | Preenchimento |
|-------|-----------|----------|------|---------------|
| `ap_despesaApresentado` | DESPESA_CAIXA | 19 | R$ 5.079,67 | 100.0% |
| `ap_despesaApurado` | DESPESA_CAIXA | 19 | R$ 5.079,67 | 100.0% |
| `ap_despesaDiferenca` | DESPESA_CAIXA | 0 | R$ 0,00 | 100.0% |
| `ap_valeFunApresentado` | VALE_FUNCIONARIO | 13 | R$ 19.989,91 | 100.0% |
| `ap_valeFunApurado` | VALE_FUNCIONARIO | 13 | R$ 19.989,91 | 100.0% |
| `ap_valeFunDiferenca` | VALE_FUNCIONARIO | 0 | R$ 0,00 | 100.0% |
| `ap_emprestimoApurado` | EMPRESTIMO | 0 | R$ 0,00 | 100.0% |
| `ap_emprestimoDiferenca` | EMPRESTIMO | 0 | R$ 0,00 | 100.0% |
| `ap_suprimentoCaixa` | SUPRIMENTO | 0 | R$ 0,00 | 100.0% |
| `ap_fundoCaixaCredito` | FUNDO_CAIXA | 0 | R$ 0,00 | 100.0% |
| `ap_fundoCxDebApurado` | FUNDO_CAIXA | 0 | R$ 0,00 | 100.0% |
| `ap_fundoCxDebDiferenca` | FUNDO_CAIXA | 0 | R$ 0,00 | 100.0% |
| `ap_transfBancApurado` | OUTROS | 15 | R$ 70.598,94 | 100.0% |

## Top PDV por despesaApurado (7d)

| PDV | Despesa apurada |
|-----|-----------------|
| 56764 | R$ 1.857,00 |
| 54193 | R$ 1.806,14 |
| 15880 | R$ 1.416,53 |

## Conclusão forense

Despesas de caixa existem como **`despesaApurado` / `despesaApresentado` / `despesaDiferenca`** em CAIXA_APRESENTADO. Sangria explícita **não** identificada. Suprimento presente como campo, porém **zerado** na janela 7d.
