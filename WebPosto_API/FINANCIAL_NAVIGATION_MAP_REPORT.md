# IA-6 — Financial Navigation Map Report

## Receitas

```text
Sidebar 💰 Financeiro
  └─ Tab Receitas (receitas)
       └─ view: dashboard
            └─ app.js: refreshAll → fetchFinancialOverview(filters)
                 └─ api.js: GET /v1/financial/overview
                      └─ fechamento_enterprise.financial_overview()
                           └─ NetworkFinancialOverviewService.get_financial_overview_only()
                                ├─ _load_filtered_expenses()
                                │    └─ WebPostoClient.call_endpoint("despesas_financeiro_rede")
                                │         └─ /INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE  ⚠️ FALHA AQUI
                                └─ _fetch_titulo_pagar() por filial (não alcançado se despesas falha)
                                     └─ /INTEGRACAO/TITULO_PAGAR
```

## Despesas

```text
Sidebar 💰 Financeiro
  └─ Tab Despesas (despesas)
       └─ view: expenses
            └─ app.js: fetchDatasetAcrossCompanies(fetchFinancialExpenses)
                 └─ api.js: GET /v1/financial/expenses
                      └─ fechamento_enterprise.financial_expenses()
                           └─ NetworkFinancialOverviewService.get_financial_expenses()
                                └─ _load_screen_expenses() / lineage pipeline
                                     └─ WebPostoClient.call_endpoint("despesas_financeiro_rede")
                                          └─ /INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE  ⚠️ FALHA AQUI
```

## Endpoint compartilhado

| View | Endpoint API | Upstream WebPosto |
|------|--------------|-------------------|
| Receitas (`dashboard`) | `/v1/financial/overview` | `CONSULTAR_DESPESAS_FINANCEIRO_REDE` |
| Despesas (`expenses`) | `/v1/financial/expenses` | `CONSULTAR_DESPESAS_FINANCEIRO_REDE` |

**Ambas dependem do mesmo upstream live.**

## Parecer IA-6

Mapa completo confirmado. Gargalo único: **`despesas_financeiro_rede`**.
