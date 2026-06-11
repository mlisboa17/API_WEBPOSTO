# DW PDV EXPENSE MODEL — F03.1

**Status:** especificação pronta · DDL físico pendente F03.2

---

## Facts

### fact_pdv_expense

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| pdv_expense_sk | INTEGER PK | Surrogate |
| cash_closing_sk | INTEGER FK | → fact_cash_closing |
| pdv_sk | INTEGER FK | → dim_pdv |
| operator_sk | INTEGER FK | → dim_operator |
| turn_sk | INTEGER FK | → dim_turn |
| category_sk | INTEGER FK | → dim_pdv_expense_category |
| valor_apurado | REAL | despesaApurado |
| valor_apresentado | REAL | despesaApresentado |
| valor_diferenca | REAL | despesaDiferenca |
| categoria_pdv_despesa | TEXT | enum classificação |
| confidence_score | REAL | 0–1 |
| classification_source | TEXT | regra aplicada |
| loaded_at | TEXT | audit trail |

**Grain:** caixaCodigo + categoria + dataMovimento

### fact_pdv_expense_reconciliation

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| reconciliation_sk | INTEGER PK | |
| pdv_expense_sk | INTEGER FK | |
| despesas_rede_id | TEXT | NK rede |
| match_status | TEXT | MATCHED/UNMATCHED/DUPLICATE |
| valor_caixa | REAL | |
| valor_rede | REAL | |
| delta_valor | REAL | paridade 0,00 |
| plano_conta | TEXT | |
| centro_custo | TEXT | |
| loaded_at | TEXT | |

---

## Dimensions

| Dim | NK |
|-----|-----|
| dim_pdv_expense_category | category_code |
| dim_cash_register | caixaCodigo |
| dim_operator | funcionarioCodigo |
| dim_pdv | pdvCodigo |
| dim_turn | turnoCodigo |

## Join keys

```text
fact_pdv_expense.cash_closing_sk → fact_cash_closing
fact_pdv_expense_reconciliation ← crosscheck (empresa, data, valor)
```
