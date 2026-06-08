# DW READINESS 2.0

## Dimensões

| Objeto | DDL | Status |
|--------|-----|--------|
| dim_plano_conta | dw/ddl/dim_plano_conta.sql | ✅ |
| dim_centro_custo | dw/ddl/dim_centro_custo.sql | ✅ |
| dim_supplier | dw/ddl/dim_supplier.sql | ✅ MDM |
| dim_supplier_category | dw/ddl/dim_supplier_category.sql | ✅ |

## Fatos

| Objeto | Status |
|--------|--------|
| fact_expense_v2 | ✅ DDL |
| fact_payables / receivables / cash / bank | ✅ DDL |
| fact_supplier_expense/payable/bank | ✅ DDL |
| fact_supplier_cost/dependency/strategy | ✅ DDL F01.4-D |
| fact_supplier_purchase | Future Ready (401) |

## DW Readiness

**~85%** — pronto para A04 carga; pendente ETL e catálogos 401.
