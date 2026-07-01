# RT00_FLOW_INVENTORY_REPORT — IA-6

**Data:** 2026-06-14 | **Período teste:** 2026-06-01 → 2026-06-07

## Legenda

| Status fluxo | Significado |
|---|---|
| **COMPLETO** | Tela → API → Serviço → Snapshot → Dados exibidos |
| **PARCIAL** | Alguma etapa lenta ou fallback |
| **QUEBRADO** | Tela não exibe dados |

---

## Fluxo 1 — Financial Operations Center ✅ COMPLETO

```text
/app/financial?view=financial-operations-center
  → fetchFinancialOperationsCenter() [api.js]
  → GET /api/v1/financial/operations-center/cockpit
  → FinancialOperationsCenterService (read-only snapshots)
  → snapshots/financial/* + scheduler + health
  → Cockpit renderizado (~1,1s)
```

## Fluxo 2 — Financial Intelligence ✅ COMPLETO

```text
?view=financial-intelligence
  → GET /api/v1/financial/intelligence-center/cockpit
  → FinancialIntelligenceCenterService
  → snapshots/financial/* (evidence loader)
  → Score + trends + risks (~0,35s)
```

## Fluxo 3 — Despesas ⚠ PARCIAL

```text
?view=expenses
  → fetchFinancialExpenses()
  → GET /v1/financial/expenses
  → FinancialResilienceService (live 22s budget)
  → fallback financial_expenses snapshot
  → Tabela despesas (≤22s)
```

## Fluxo 4 — Vendas combustível ⚠ PARCIAL (P0 corrigido)

```text
?view=sales
  → fetchSales()
  → GET /v1/sales
  → SalesResilienceService (live 8s budget)
  → fallback financial_sales snapshot
  → Tabela vendas (~8s 1ª req, ~0s circuit OPEN)
```

## Fluxo 5 — Overview receitas ⚠ PARCIAL

```text
?view=dashboard
  → fetchFinancialOverview + multi-fetch
  → GET /v1/financial/overview
  → NetworkFinancialOverviewService (live multi-filial)
  → snapshot F08 se falha
  → Lento (>6s probe)
```

## Fluxo 6 — Produtos vendidos ⚠ PARCIAL

```text
?view=nonFuelProducts
  → GET /api/v1/non-fuel-products/cockpit
  → NonFuelProductSalesSnapshotService
  → snapshots/non_fuel_products/
  → OK (~1,8s)
```

## Fluxo 7 — Fiscal NFCE ⚠ PARCIAL

```text
?view=nfceIntelligence
  → GET /api/v1/nfce-intelligence/cockpit
  → snapshot nfce_intelligence
  → OK (<0,1s)
```

## Fluxo 8 — Combustível fuels/bombas ❌ PARCIAL (live)

```text
?view=fuels
  → GET /api/v1/sales/fuel-summary
  → analytics live WebPosto
  → timeout probe 6s
  → Dados incompletos no frontend
```

## Fluxo 9 — Administração ⚠ PARCIAL (placeholder)

```text
?view=administration
  → renderAdministration()
  → Sem API backend CRUD
  → UI estática
```

## Fluxo 10 — Executivo IA ⚠ PARCIAL

```text
?view=executiveCopilot
  → GET /api/v1/executive-copilot/*
  → IA generativa F05
  → Snapshot parcial
  → Experimental
```

## Resumo fluxos

| Status | Qtd |
|---|---|
| COMPLETO | 2 |
| PARCIAL | 8 |
| QUEBRADO | 0 |
