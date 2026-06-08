# ANALYTICS CONSOLIDATION PLAN — LOGOS SPACE
## Sprint A02.5 | Agente 3 — Analytics

| Campo | Valor |
|---|---|
| **Engines paralelas KPI** | 3 |
| **Target** | 1 engine por domínio |
| **Data** | 2026-06-08 |

---

## Mapeamento de Engines

| Domínio | Engine Oficial | Engines Duplicadas | Arquivo |
|---|---|---|---|
| **KPI** | `AnalyticsService.get_kpis()` | `fetch_executive_kpis`, `get_executive_metrics`, `metricsEngine.js` | `analytics_service.py` |
| **DRE** | `AnalyticsService.get_dre()` | `analyticsEngine.js` (client), `FinancialReconciliationEngine` | `analytics_service.py` |
| **Fuel físico** | `FuelAnalyticsService` + `FuelKpiEngine` | — | `fuel_analytics_service.py` |
| **Fuel comercial** | `AnalyticsService.get_fuel_summary()` | `build_adelaide_metrics` (parcial) | `analytics_service.py` |
| **Coverage** | `build_network_coverage()` | — | `executive_snapshot_service.py` |
| **Data Quality** | `DataQualityService` | — | `data_quality_service.py` |
| **Snapshot** | `ExecutiveSnapshotService` | `FinancialSnapshotService` (legado) | `executive_snapshot_service.py` |
| **Reconciliação** | `FinancialReconciliationEngine` | scripts ad-hoc | `financial_reconciliation_engine.py` |

---

## Fluxos Paralelos (Conflitos)

| Conflito | Risco | Decisão |
|---|---|---|
| KPI comercial (Analytics) vs fiscal (Adelaide) | Números divergentes | Analytics = gerencial; Adelaide = fiscal (deprecar Adelaide no 8040) |
| Fuel LMC vs VENDA_ITEM | Métricas diferentes | Manter separados; renomear na UI |
| KPIs via `/api/v1/kpis` vs `/api/executive/kpis` (8050) vs `/metrics/executive` | 3 fontes | Unificar em `/api/v1/kpis` + snapshot |
| Cálculo DRE no frontend (`analyticsEngine.js`) | Divergência classificação | Deprecar cálculo JS; API only |

---

## Plano de Depreciação

### Curto prazo (A03)

| Ação | Alvo |
|---|---|
| Deprecar `/api/executive/kpis` (8050) | Redirect → `/api/v1/kpis` |
| Deprecar `/metrics/executive` | Redirect → `/api/v1/executive/snapshot` |
| Documentar contrato LMC vs Vendidos na UI | Label explícito |

### Médio prazo (A03-A04)

| Ação | Alvo |
|---|---|
| Mover agregação multiselect para backend | `AnalyticsService` |
| Unificar normalização monetária | `money_normalizer.py` shared |
| Limpar `analyticsEngine.js` — só formatação | Frontend |

### Longo prazo (A04+)

| Ação | Alvo |
|---|---|
| Mover engines para `src/analytics/` | kpi_engine, fuel_engine, snapshot_service |
| Deprecar `fetch_executive_kpis` | Absorver em AnalyticsService ou remover |
| Deprecar `FinancialSnapshotService` | Absorver em ExecutiveSnapshotService |

---

## Target State

```
src/analytics/
├── kpi_engine.py      ← AnalyticsService (KPI + DRE)
├── fuel_engine.py     ← FuelAnalyticsService + FuelKpiEngine
├── commercial_fuel.py ← get_fuel_summary (renomeado)
├── quality_engine.py  ← DataQualityService
├── coverage_engine.py ← build_network_coverage
├── snapshot_service.py← ExecutiveSnapshotService
└── reconciliation.py  ← FinancialReconciliationEngine
```

---

*Agente 3 — sem alteração de código nesta sprint.*
