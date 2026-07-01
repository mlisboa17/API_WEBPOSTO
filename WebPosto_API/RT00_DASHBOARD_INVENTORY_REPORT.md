# RT00_DASHBOARD_INVENTORY_REPORT — IA-5

**Data:** 2026-06-14 | **Plataforma:** SPA única `/app/financial`

## Definição

No LOGOS SPACE, cada `?view=` é um dashboard dentro do cockpit único. Não há URLs separadas por dashboard.

## Dashboards por área

### OPERACIONAL (dados snapshot, carrega <3s, sem erro JS conhecido)

| Dashboard | View | API principal | Dados coerentes |
|---|---|---|---|
| Financial Operations Center | financialOperationsCenter | `/api/v1/financial/operations-center/cockpit` | Sim (read-only) |
| Financial Intelligence | financialIntelligence | `/api/v1/financial/intelligence-center/cockpit` | Sim (read-only) |

### PARCIAL (carrega shell; dados live lentos ou placeholder)

| Dashboard | View | Problema |
|---|---|---|
| Despesas | expenses | Live ≤22s ou snapshot |
| Vendas combustível | sales | ~8s fallback P0 |
| Receitas/overview | dashboard | Live lento |
| Produtos vendidos | nonFuelProducts | Depende período |
| NFCE / Fiscal | nfce*, fiscal* | Snapshot OK, UI parcial |
| Executivo workspace | executiveWorkspace | Multi-fetch |
| Administração | administration | **Placeholder** (sem CRUD) |
| Combustível executive | fuelExecutive | OK ~2s |
| Fluxo caixa | cashFlow | Snapshot pequeno (90 bytes probe) |
| Monitoring F08.2 | financialMonitoring | Duplicata legado |
| Operations F08.2 | financialOperations | Duplicata legado |

### Motor strip (acessível via navegação secundária, sem aba)

| Dashboard | View | Status |
|---|---|---|
| Benchmark | benchmark | PARCIAL |
| Corporate Hub | corporateHub | PARCIAL |
| Executive Copilot | executiveCopilot | PARCIAL (IA) |
| Recommendations | recommendations | PARCIAL (IA) |
| Learning | learning | PARCIAL (IA) |
| Operator Performance | operatorPerformance | PARCIAL |
| People Intelligence | peopleIntelligence | PARCIAL |

## Validação JS

| Check | Resultado |
|---|---|
| Shell carrega | OK (app.js module) |
| Erro JS global conhecido | Nenhum reportado no inventário |
| Timeout UX | Sim — `apiClient.js` 30–45s |
| Modo degradado | Sim — `allowDegraded` sales/expenses |

## Contagem

| Status | Dashboards |
|---|---|
| OPERACIONAL | 2 |
| PARCIAL | 36+ |
| QUEBRADO (shell) | 0 |
