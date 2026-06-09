# DW GOVERNANCE REPORT — Release 2.0

**Data:** 2026-06-08 · DDL em `dw/ddl/` (21 arquivos)

---

## Objetos validados (sprint)

| Objeto | Arquivo DDL | Linhas | Status |
|--------|-------------|--------|--------|
| `dim_plano_conta` | `dim_plano_conta.sql` | 29 | ✅ Completo |
| `dim_centro_custo` | `dim_centro_custo.sql` | 19 | ✅ Completo |
| `dim_supplier` | `dim_supplier.sql` | 27 | ✅ MDM VIBRA/OEC |
| `fact_supplier_expense` | `fact_supplier_expense.sql` | 20 | ✅ |
| `fact_supplier_payable` | `fact_supplier_payable.sql` | 21 | ✅ |
| `fact_supplier_bank` | `fact_supplier_bank.sql` | 15 | ✅ |
| `fact_supplier_cost` | `fact_supplier_cost.sql` | 21 | ✅ F01.4-D |
| `fact_supplier_dependency` | `fact_supplier_dependency.sql` | 16 | ✅ F01.4-D |
| `fact_supplier_strategy` | `fact_supplier_strategy.sql` | 18 | ✅ F01.4-D |

### Dimensões complementares

| Objeto | Status |
|--------|--------|
| `dim_supplier_category` | ✅ F01.4-D |
| `dim_account`, `dim_financial_category` | ✅ F01.4-A/B |
| `dim_company`, `dim_cost_center`, `dim_date` | ✅ Core |

### Fatos complementares

| Objeto | Status |
|--------|--------|
| `fact_expense_v2` | ✅ |
| `fact_payables`, `fact_receivables` | ✅ |
| `fact_cash`, `fact_bank_movements` | ✅ |
| `fact_supplier_purchase` | ⚠️ Future Ready (401 NOTA_ENTRADA) |

---

## Readiness

| Métrica | Valor | Notas |
|---------|-------|-------|
| **DW Readiness** | **85%** | DDL completo; ETL não implementado |
| **Data Mart Readiness** | **78%** | Fatos supplier prontos; falta pipeline + 401 endpoints |
| **Pronto para A04?** | **SIM (DDL)** / **NÃO (ETL)** | Iniciar A04 com carga `dim_supplier` + `fact_supplier_cost` |

---

## Lacunas A04

1. Pipeline ETL Python/Airflow inexistente
2. `CENTRO_CUSTO_REDE`, `NOTA_ENTRADA` — 401 token
3. `fact_supplier_purchase` aguarda COMPRA_REDE
4. Ambiente Postgres/Supabase não provisionado no repo
5. Testes de integração DW ausentes

---

## Respostas obrigatórias

1. **DW Readiness %:** **85%**
2. **Data Mart Readiness %:** **78%**
3. **Pronto para A04?** **Parcialmente** — DDL aprovado; ETL é próximo sprint

**Veredito:** **APROVADO** para iniciar A04 (fase DDL + desenho ETL).
