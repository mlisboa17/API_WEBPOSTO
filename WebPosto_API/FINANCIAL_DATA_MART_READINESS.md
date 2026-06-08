# FINANCIAL DATA MART READINESS — F01.4-B

## Prontidão geral: **~72%**

| Área | % | Notas |
|------|---|-------|
| fact_expense_v2 | 85% | DESPESAS_REDE + V3 |
| fact_payables | 80% | TITULO_PAGAR centro 100% |
| fact_receivables | 60% | API ok, carga A04 |
| fact_cash | 55% | parcial |
| fact_bank_movements | 50% | plano parcial |
| dim_account | 90% | 200 planos mapeados |
| dim_cost_center | 65% | catálogo 401 HTTP 401 |
| dim_company | 70% | empresas via despesas |
| dim_supplier | 45% | fornecedor parcial |
| dim_date | 100% | DDL pronto |
| dim_financial_category | 95% | V3 operacional |

## Dependências Quality

- LANCAMENTO_CONTABIL vazio
- CENTRO_CUSTO_REDE 401
- Receita via TITULO_RECEBER incompleta

DRE cobertura: **89.81%** · Data Quality: **83.7**
