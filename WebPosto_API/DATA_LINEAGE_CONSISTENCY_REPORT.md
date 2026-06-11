# DATA LINEAGE & CONSISTENCY — D04 · IA-6

| Métrica | Valor |
|---------|-------|
| Consistency % | **100.0** |
| Campos órfãos | 0 |
| Indicadores órfãos | 0 |
| Lineage quebrado | **Não** |

## Lineage (amostra)

| Indicador | Fonte | Snapshot | API | Cockpit |
|---|---|---|---|---|
| Corporate Score | None | executive_scorecard | /api/v1/corporate-hub/cockpit | corporate-hub |
| Financial Hub | None | cash_operations_qa | /api/v1/corporate-hub/cockpit | corporate-hub |
| People Hub | None | people_intelligence | /api/v1/corporate-hub/cockpit | corporate-hub |
| Operations Hub | None | store_shift_profitability | /api/v1/corporate-hub/cockpit | corporate-hub |
| Receita Operacional | F04.3 | store_shift_profitability | /api/v1/store-shift-profitability | operation-roi |
| Cash Paridade | F03.3 | cash_operations_qa | /api/v1/cash-operations | cash-operations |
| People Score | F04.1 | people_intelligence | /api/v1/operator-accountability-incentive/cockpit | people-intelligence |
