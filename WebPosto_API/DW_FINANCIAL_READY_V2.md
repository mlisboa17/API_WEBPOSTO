# DW FINANCIAL READY V2 — F01.4-B

## Fatos modelados

| Fato | DDL | Granularidade |
|------|-----|---------------|
| fact_expense_v2 | dw/ddl/fact_expense_v2.sql | 1 despesa gerencial |
| fact_payables | dw/ddl/fact_payables.sql | 1 título pagar |
| fact_receivables | dw/ddl/fact_receivables.sql | 1 título receber |
| fact_cash | dw/ddl/fact_cash.sql | 1 movimento caixa |
| fact_bank_movements | dw/ddl/fact_bank_movements.sql | 1 movimento banco |

## Dimensões

| Dimensão | DDL | Status |
|----------|-----|--------|
| dim_account | dim_account.sql (view) | ✅ |
| dim_cost_center | dim_cost_center.sql (view) | ✅ |
| dim_company | dim_company.sql | ✅ |
| dim_supplier | dim_supplier.sql | ✅ |
| dim_date | dim_date.sql | ✅ |
| dim_financial_category | dim_financial_category.sql | ✅ |

## Particionamento / Historização

- Partição mensal sugerida em `data_lancamento` (A04)
- SCD Type 1 em dimensões (F01.4-A)
- Índices por company_sk, date_sk, account_sk
