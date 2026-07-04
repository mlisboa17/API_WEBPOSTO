# VALUE-04 — Runtime Report

**Executado:** 2026-07-04

## Discovery (3 detectores × 3 tenants)

| tenant | detector | signal | impact | conf | state |
|---|---|---|---:|---:|---|
| 74014 | ExpenseDetector | CATEGORY_SPIKE | 11251.5 | 89% | DECISION |
| 11495 | CardReceivableDetector | OVERDUE_RECEIVABLE | 3970.9 | 75% | OBSERVATION |
| 74014 | CardReceivableDetector | OVERDUE_RECEIVABLE | 5221.6 | 50% | OBSERVATION |

**Vencedor global:** ExpenseDetector (74014) — priority 52,63

**CardReceivable:** 2 observações, 0 decisions (LEVEL 1 + confidence < 80%)

## Performance

| Métrica | 1º cold (sem cache) | Warm |
|---|---:|---:|
| FULL_ANALYSIS | 121,2 s | 2,4 ms |
| WebPosto requests | 165 | 0 |
| receivable cache | 3 miss / 3 hit | 6 hit |

HOME (PERFORMANCE-01 script): ~2,6 ms | REFRESH trigger: ~16 ms

## Limitações

- Cartão TEF: sem NSU/bandeira/adquirente
- VENDA_FORMA_PAGAMENTO: 0 registros nos 3 postos (30d)
- Conciliação cartão↔recebível: impossível transacional
