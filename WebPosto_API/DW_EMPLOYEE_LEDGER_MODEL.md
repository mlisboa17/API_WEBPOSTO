# DW EMPLOYEE LEDGER MODEL — F03.3 · Agente 10

## Facts

| Fact | Descrição |
|------|-----------|
| `fact_employee_cash_ledger` | Eventos FALTA/SOBRA/AJUSTE/VALE/TÍTULO |
| `fact_employee_balance` | Saldo líquido por operador |
| `fact_cash_accountability` | Destino das diferenças |
| `fact_management_expense` | Despesas com classificação gerencial |

## Dimensions

| Dim | Valores |
|-----|---------|
| `dim_employee` | funcionarioCodigo |
| `dim_management_group` | OPERACIONAL, PESSOAL, TESOURARIA, PERDAS, ADMINISTRATIVO, FINANCEIRO |
| `dim_management_class` | SALARIO, VALE, PERDA_CAIXA_FUNCIONARIO, ... |
| `dim_dre_impact` | SIM, NAO, PARCIAL |
| `dim_cashflow_impact` | SIM, NAO, PARCIAL |

## Status

Modelo documentado — pronto para ingestão ETL F03.4.
