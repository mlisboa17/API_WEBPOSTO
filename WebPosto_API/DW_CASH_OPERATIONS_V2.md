# DW CASH OPERATIONS V2 — F02.1-B

Evolução do modelo F02.1-A com evidência root-cause.

## Facts (prontos para DDL F03)

| Fact | Grain | Medidas | Status |
|------|-------|---------|--------|
| fact_cash_closing | caixaCodigo + dataMovimento | apurado, diferenca, abertura, fechamento | ✅ especificado |
| fact_cash_difference | cash_closing_sk | amount, difference_type | ✅ especificado |
| fact_cash_component | cash_closing_sk + component | apresentado, apurado, diferenca | ✅ especificado |
| fact_cash_operator | employee_sk + date_sk | fechamentos, diff_total, p95 | ✅ especificado |
| fact_cash_shift | turn_sk + date_sk | fechamentos, diff_total, duracao_horas | ✅ especificado |

## Dimensions

| Dim | NK | Fonte | Status |
|-----|-----|-------|--------|
| dim_employee | funcionarioCodigo | CAIXA | ✅ join validado |
| dim_pdv | pdvCodigo | CAIXA | ✅ |
| dim_turn | turnoCodigo | CAIXA | ✅ |
| dim_cash_register | caixaCodigo | CAIXA | ✅ |
| dim_cash_component | component_code | CAIXA_APRESENTADO | ✅ |

## Join keys (evidência 7d)

```text
CAIXA.caixaCodigo = CAIXA_APRESENTADO.caixaCodigo
CAIXA.empresaCodigo = CAIXA_APRESENTADO.empresaCodigo
dinheiroDiferenca ≈ diferenca (QA: True)
```

**DDL físico:** pendente F03 (sprint investigativa — sem CREATE TABLE).
