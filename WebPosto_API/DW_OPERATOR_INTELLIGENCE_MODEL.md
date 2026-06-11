# DW OPERATOR INTELLIGENCE MODEL — F04.0 · Agente 10

## Dimensions

| Tabela | Arquivo | Chave |
|--------|---------|-------|
| dim_employee | `dw/ddl/dim_employee.sql` | funcionario_codigo |
| dim_pdv | `dw/ddl/dim_pdv.sql` | pdv_codigo |
| dim_turn | `dw/ddl/dim_turn.sql` | turno_codigo |
| dim_date | `dw/ddl/dim_cash_date.sql` | date_sk |

## Facts

| Tabela | Arquivo |
|--------|---------|
| fact_operator_sales | `dw/ddl/fact_operator_sales.sql` |
| fact_operator_discount | `dw/ddl/fact_operator_discount.sql` |
| fact_operator_productivity | `dw/ddl/fact_operator_productivity.sql` |
| fact_operator_risk | `dw/ddl/fact_operator_risk.sql` |
| fact_operator_accountability | `dw/ddl/fact_operator_accountability.sql` |

Paridade auditada: **0.0** · OK: **Não**
