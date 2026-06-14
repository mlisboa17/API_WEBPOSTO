# IA-2 — Financial Route Resolution Report

## Financeiro → Receitas

| Camada | Valor |
|--------|-------|
| Área sidebar | `financeiro` |
| Tab | `receitas` |
| View frontend | `dashboard` |
| Seção DOM | `#dashboardView` |
| Renderer | `frontend/pages/dashboard.js` → `renderDashboard()` |
| Loader app.js | `fetchFinancialOverview(state.filters)` |
| API frontend | `GET /v1/financial/overview` |
| Rota backend | `fechamento_enterprise.py` → `financial_overview()` |
| Service | `NetworkFinancialOverviewService.get_financial_overview_only()` |
| WebPosto live | `call_endpoint("despesas_financeiro_rede")` + `call_endpoint("financeiro")` por filial |

## Financeiro → Despesas

| Camada | Valor |
|--------|-------|
| Área sidebar | `financeiro` |
| Tab | `despesas` |
| View frontend | `expenses` |
| Seção DOM | `#expensesView` |
| Renderer | `frontend/pages/expenses.js` → `renderExpenses()` |
| Loader app.js | `fetchDatasetAcrossCompanies(fetchFinancialExpenses, ...)` |
| API frontend | `GET /v1/financial/expenses` |
| Rota backend | `fechamento_enterprise.py` → `financial_expenses()` |
| Service | `NetworkFinancialOverviewService.get_financial_expenses()` |
| WebPosto live | `call_endpoint("despesas_financeiro_rede")` (+ lineage/semantic em memória) |

## Mapeamento navigation.js

```javascript
{ id: "receitas", label: "Receitas", view: "dashboard" },
{ id: "despesas", label: "Despesas", view: "expenses" },
```

## Parecer IA-2

Rotas frontend e backend **existem e estão corretamente encadeadas**. O gargalo está no **upstream WebPosto** via `despesas_financeiro_rede`, não na resolução de view.
