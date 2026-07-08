# FIN-02 — Financial Review Assignment (runtime)

## Primeira execução (assignment real)

Ver `FIN_02_FINANCIAL_REVIEW_ASSIGNMENT_RUNTIME_FIRST.json`

| Campo | Valor |
|-------|-------|
| POST assign | 200 |
| status antes | REQUESTED |
| status depois | ASSIGNED |
| responsável | Marcio de Lima |
| detail antes (s) | 0.14 |
| detail depois (s) | 0.05 |
| detail_fast_path | true |
| PASS | true |

## Re-execução idempotente

Ver `FIN_02_FINANCIAL_REVIEW_ASSIGNMENT_RUNTIME.json`

| Campo | Valor |
|-------|-------|
| POST assign | 200 |
| assign_idempotent | true |
| status | ASSIGNED |
| responsável | Marcio de Lima |
| detail_fast_path | true |
| PASS | true |
