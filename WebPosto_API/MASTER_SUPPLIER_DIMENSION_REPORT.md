# MASTER SUPPLIER DIMENSION REPORT — F01.4-C

| Métrica | Valor |
|---------|-------|
| Fornecedores únicos (raw) | **28** |
| Fornecedores canônicos | **28** |
| SupplierCoverageScore médio | **94.3** |

DDL: `dw/ddl/dim_supplier.sql`

## Deduplicação

Regras determinísticas: IPIRANGA*, AMBEV*, VIBRA* → grupos canônicos.
