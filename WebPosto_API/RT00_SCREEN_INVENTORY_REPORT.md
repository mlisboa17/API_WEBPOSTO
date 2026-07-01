# RT00_SCREEN_INVENTORY_REPORT — IA-1

**Data:** 2026-06-14 | **Base:** `http://127.0.0.1:8050/app/financial` | **Método:** código + probe HTTP shell

## Resumo

| Métrica | Valor |
|---|---|
| URL única de entrada | `/app/financial` |
| Views mapeadas (`?view=`) | **40** |
| Módulos `frontend/pages/*.js` | **41** |
| Shell HTML (200 OK) | **4296 bytes**, ~0,02s |
| Áreas de navegação (UX-01) | **6** |

## Inventário por área

### Executivo (6 views principais)

| View | URL | Renderiza shell | Dados | Classificação |
|---|---|---|---|---|
| executiveWorkspace | `?view=executive-workspace` | Sim | Snapshot parcial | **PARCIAL** |
| executiveScorecard | `?view=executive-scorecard` | Sim | Snapshot | **PARCIAL** |
| actionCenter | `?view=action-center` | Sim | Snapshot | **PARCIAL** |
| goalsCampaign | `?view=goals-campaigns` | Sim | Snapshot | **PARCIAL** |
| dashboard | `?view=dashboard` | Sim | Live lento | **PARCIAL** |
| executive | `?view=executive` | Sim | Live | **PARCIAL** |

Motors sem aba direta (motor strip): `benchmark`, `corporateHub`, `executiveDecision`, `executiveCopilot`, `recommendations`, `learning` — **PARCIAL**

### Financeiro (14 views)

| View | URL alias | Classificação |
|---|---|---|
| expenses | `?view=expenses` | **PARCIAL** (resilience F08, live ≤22s) |
| accounts | `?view=accounts` | **PARCIAL** |
| cashFlow | `?view=cash-flow` | **PARCIAL** |
| cashOperations | `?view=cash-operations` | **PARCIAL** |
| financeCenter | `?view=finance-center` | **PARCIAL** |
| financialOperationsCenter | `?view=financial-operations-center` | **OPERACIONAL** (snapshot read-only) |
| financialIntelligence | `?view=financial-intelligence` | **OPERACIONAL** (snapshot read-only) |
| financialMonitoring | `?view=financial-monitoring` | **PARCIAL** (legado F08.2 UI) |
| financialOperations | `?view=financial-operations` | **PARCIAL** (legado F08.2 UI) |
| operatorPerformance | motor | **PARCIAL** |
| peopleIntelligence / peopleRoi / operationRoi / managementAction | motor | **PARCIAL** |

### Combustíveis (6 views)

| View | Classificação | Nota |
|---|---|---|
| sales | **PARCIAL** | Hotfix P0: ~8s snapshot fallback |
| stock | **PARCIAL** | Live WebPosto lento |
| fuels | **PARCIAL** | Timeout histórico |
| fuelExecutive | **PARCIAL** | API `/api/v1/fuel/executive` OK |
| lmcIntelligence | **PARCIAL** | Snapshot cockpit |
| fuelGovernance | **PARCIAL** | Snapshot cockpit OK |

### Produtos Vendidos (4 views distintas, 3 módulos)

| View | Classificação |
|---|---|
| nonFuelProducts | **PARCIAL** |
| commercialCopilot / commercialExecution / commercialLearning | **PARCIAL** (cockpits snapshot OK) |

### Fiscal (3 views)

| View | Classificação |
|---|---|
| nfceIntelligence | **PARCIAL** |
| fiscalReconciliation | **PARCIAL** |
| fiscalIntelligence | **PARCIAL** |

### Administração (1 view)

| View | Classificação |
|---|---|
| administration | **PARCIAL** (UI placeholder, sem CRUD real) |

## Classificação global telas

| Status | Qtd | % |
|---|---|---|
| **OPERACIONAL** | 2 | 5% |
| **PARCIAL** | 38 | 95% |
| **QUEBRADA** | 0 | 0% |

> **Nota:** Nenhuma view quebra o shell HTML. Quebras são de **dados/API** (timeout live), não de renderização.

## Evidência

```text
GET /app/financial → 200, 4296 bytes, 0,02s (todas as views)
```

Script: `scripts/audit_rt00_operational_inventory.py`
