# DW CASH EXPENSE RECONCILIATION — F03.1-A

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
