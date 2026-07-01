# RT00_MODULE_INVENTORY_REPORT — IA-3

**Data:** 2026-06-14

## Matriz por domínio

| Módulo | UI | API | Snapshot | Serviço | Uso operacional | Status |
|---|---|---|---|---|---|---|
| **Financeiro** | Sim (14 views) | Sim `/v1` + `/api/v1/financial/*` | Sim `snapshots/financial/` (18 arq.) | F08.0–F08.4 | Homologação ativa | **PARCIAL** |
| **Combustíveis** | Sim (6 views) | Sim `/v1/sales`, `/v1/stock`, analytics | Sim `fuel_governance`, `fuel/` | NetworkFinancialOverview | Live lento | **PARCIAL** |
| **Produtos Vendidos** | Sim (4 tabs) | Sim `/api/v1/non-fuel-products/*` | Sim (7 arq.) | F07.x engines | Cockpit OK | **PARCIAL** |
| **Fiscal** | Sim (3 views) | Sim `/api/v1/nfce-*`, `fiscal-*` | Sim (5+ arq.) | F06.x | Snapshot read | **PARCIAL** |
| **Executivo** | Sim (6+ views) | Sim 15+ routers F04–F05 | Sim `executive/` (19 arq.) | Scorecard, hub, IA | Snapshot read | **PARCIAL** |
| **Administração** | Sim (placeholder) | Circuit breaker admin | Parcial | F08 admin | Limitado | **PARCIAL** |
| **People/Operações** | Motor strip | Sim performance, people-* | Sim operator_* | F04.x | Sem aba dedicada | **PARCIAL** |

## Financeiro — detalhe F08

| Submódulo | Rota UI | API | Snapshot kind | Status |
|---|---|---|---|---|
| Overview/Receitas | dashboard | `/v1/financial/overview` | financial_overview | PARCIAL |
| Despesas | expenses | `/v1/financial/expenses` | financial_expenses | PARCIAL |
| Contas | accounts | `/v1/financial/accounts-*` | payables/receivables | PARCIAL |
| Fluxo caixa | cashFlow | `/api/v1/finance/cash-flow/*` | cash_flow | PARCIAL |
| Extratos | cashOperations | `/api/v1/cash/operations/*` | cash_operations | PARCIAL |
| Conciliação | financeCenter | `/api/v1/finance/center/*` | finance_center | PARCIAL |
| Operations Center | financialOperationsCenter | `/api/v1/financial/operations-center/*` | health + scheduler | **OPERACIONAL** |
| Intelligence | financialIntelligence | `/api/v1/financial/intelligence-center/*` | financial intelligence | **OPERACIONAL** |
| Monitoring (legado) | financialMonitoring | `/api/v1/financial/operations/*` | overlap F08.2 | PARCIAL |
| Operations (legado) | financialOperations | idem | overlap | PARCIAL |

## Produtos Vendidos — F07

| Engine | UI view | API prefix | Snapshot | Status |
|---|---|---|---|---|
| Non-fuel sales | nonFuelProducts | `/api/v1/non-fuel-products` | nonfuel_products | PARCIAL |
| Commercial execution | commercialExecution | `/api/v1/commercial-execution` | commercial_execution | PARCIAL |
| Commercial learning | commercialLearning | `/api/v1/commercial-learning` | commercial_learning | PARCIAL |
| Commercial copilot | commercialCopilot | `/api/v1/commercial-copilot` | commercial_copilot | PARCIAL |

## Combustíveis

| Função | UI | API | Status |
|---|---|---|---|
| Vendas rede | sales | `/v1/sales` | PARCIAL (hotfix P0) |
| Estoque/tanques | stock | `/v1/stock` | PARCIAL |
| Bombas/analytics | fuels | `/api/v1/sales/fuel-summary` | PARCIAL (timeout) |
| Executive fuel | fuelExecutive | `/api/v1/fuel/executive` | PARCIAL |
| LMC | lmcIntelligence | `/api/v1/lmc-intelligence` | PARCIAL |
| Governança | fuelGovernance | `/api/v1/fuel-governance` | PARCIAL |

## Fiscal — F06

| Função | UI | API | Status |
|---|---|---|---|
| NFCE | nfceIntelligence | `/api/v1/nfce-intelligence` | PARCIAL |
| Conciliação | fiscalReconciliation | `/api/v1/fiscal-reconciliation` | PARCIAL |
| Tributação/riscos | fiscalIntelligence | `/api/v1/fiscal-intelligence` | PARCIAL |
