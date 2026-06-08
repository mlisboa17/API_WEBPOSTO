# LOGOS SPACE — Architecture Baseline 1.1
## Sprint A02.5 — Consolidação Física da Arquitetura

| Campo | Valor |
|---|---|
| **Projeto** | LOGOS SPACE Combustíveis |
| **Sprint** | A02.5 |
| **Pré-requisitos** | A01.1 Baseline 1.0, A02 Baseline 1.0 |
| **Data** | 2026-06-08 |
| **Escopo** | Consolidação física documental — **sem alteração de código** |
| **Ambiente oficial** | `src/main.py` → porta **8040** → `/app/financial` |

---

## 1. Evolução A02 → A02.5

| Dimensão | A02 (1.0) | A02.5 (1.1) |
|---|---|---|
| Entrypoints | Tabela resumida | `ENTRYPOINT_MIGRATION.md` — 8 mapeados com routers |
| WebPosto | 1 oficial declarado | `WEBPOSTO_CONSOLIDATION_PLAN.md` — 7 clientes + SDK |
| Analytics | Engines por domínio | `ANALYTICS_CONSOLIDATION_PLAN.md` — 3 fluxos KPI mapeados |
| Fuel | Regra LMC vs Vendidos | `FUEL_ARCHITECTURE_PLAN.md` — golden path + legados |
| Dashboards | 14 legados | `DASHBOARD_CONSOLIDATION_PLAN.md` — 21 superfícies |
| Performance | Top 20 resumido | `TOP_20_PERFORMANCE_BOTTLENECKS.md` — P0/P1/P2 |
| Snapshot | Alvo declarado | `SNAPSHOT_FIRST_ARCHITECTURE.md` — 9 camadas + fases |
| Tech Debt | Matriz A02 | `TECH_DEBT_MASTER.md` — 43 itens categorizados |

---

## 2. Decisões Arquiteturais Oficiais (Definitivas)

### 2.1 EntryPoint

```
OFICIAL     = src/main.py + create_app() + porta 8040
LAUNCHER    = main.py (raiz) → src.main:app
FACTORY     = src/interfaces/http/app.py
DEPRECATED  = src/presentation/app.py (8050) — auxiliar transitório
REMOVER     = main_minimal, main-mlisboa17, explorador_standalone, logos-webposto-gateway/
```

### 2.2 Cliente WebPosto

```
OFICIAL     = src/gateway/webposto_client.py → WebPostoClient
ALVO FÍSICO = src/integrations/webposto/client.py (A03)
DUPLICADOS  = GatewayWebPostoClient, logos-webposto-gateway, httpx inline 8050
OBSOLETOS   = src/webposto/client.py, src/infrastructure/webposto/client.py, WebPostoAuditClient
```

### 2.3 Engines Analytics

| Domínio | Engine Oficial | Arquivo |
|---|---|---|
| KPI/DRE | `AnalyticsService` | `services/analytics_service.py` |
| Coverage | `build_network_coverage()` | `executive_snapshot_service.py` |
| Data Quality | `DataQualityService` | `data_quality_service.py` |
| Reconciliação | `FinancialReconciliationEngine` | `financial_reconciliation_engine.py` |
| Snapshot | `ExecutiveSnapshotService` | `executive_snapshot_service.py` |

**Engines duplicadas a eliminar:** `fetch_executive_kpis`, `get_executive_metrics`, Adelaide KPIs (8050), `metricsEngine.js` (exceto alertas).

### 2.4 Engine Fuel

| Dimensão | Engine | Endpoint | Fonte WebPosto |
|---|---|---|---|
| **Físico (oficial)** | `FuelAnalyticsService` + `FuelKpiEngine` | `/api/v1/fuel/executive` | `CONSULTAR_LMC_REDE` |
| **Comercial (oficial)** | `AnalyticsService.get_fuel_summary` | `/api/v1/sales/fuel-summary` | `VENDA_ITEM` |
| **Catálogo** | `ProdutoCatalogService` | `/api/v1/products/catalog` | `PRODUTO` |

**Regra inviolável:** LMC ≠ Vendidos — não unificar. UI: "Litros LMC" vs "Litros Vendidos".

### 2.5 Dashboard

```
OFICIAL     = frontend/index.html → /app/financial (8040)
VIEWS       = executive, fuels, sales, dashboard, expenses, accounts, stock
DEPRECATED  = static/dashboard_logos.html (Adelaide 8050)
REMOVER     = 12 HTML obsoletos + React isolado + explorador_standalone
```

### 2.6 Arquitetura Snapshot-First (Alvo A03)

```
Dashboard → Snapshot (≤8s) → Cache (60s/Valkey) → WebPosto (background only)
```

| View | Estado A02.5 | Alvo A03 |
|---|---|---|
| executive | Snapshot-first ✅ | Manter |
| fuels | Chamada direta ❌ | FuelSnapshotService |
| sales fuels | Chamada direta ❌ | Cache + snapshot |
| dashboard/expenses | Chamada direta ❌ | Snapshot parcial |

---

## 3. Inventário Consolidado

| Artefato | Quantidade | Oficial | Deprecar | Remover |
|---|---|---|---|---|
| Entrypoints | 8 | 3 | 1 | 4 |
| Clientes WebPosto | 7+SDK | 1 | 2 | 4 |
| Engines KPI | 3 fluxos | 1 | 2 | — |
| Engines Fuel | 4 fluxos | 2 (LMC+Venda) | 2 | — |
| Dashboards | 21 | 1 | 6 | 14 |
| Camadas Snapshot | 9 | 3 prontas | 3 parciais | 3 experimentais |
| Dívida técnica | 43 itens | — | — | 8 P0 |

---

## 4. Top 10 Arquivos para Remover (Prioridade)

| # | Arquivo | Motivo |
|---|---|---|
| 1 | `src/main-mlisboa17.py` | Variante pessoal — risco deploy |
| 2 | `src/main_minimal.py` | Entrypoint legado duplicado |
| 3 | `explorador_standalone.py` | Explorador experimental |
| 4 | `logos-webposto-gateway/` | Subprojeto gateway duplicado |
| 5 | `src/webposto/client.py` | Cliente obsoleto |
| 6 | `src/infrastructure/webposto/client.py` | Cliente obsoleto |
| 7 | `src/infrastructure/clients/webposto_client.py` | Audit client obsoleto |
| 8 | `src/services/vendas_combustivel_service.py` | Duplica fuel-summary |
| 9 | `dashboard_vendas.html` + `vendas-dashboard.html` | Dashboards HTML raiz |
| 10 | `src/frontend/dashboard.jsx` | React isolado não integrado |

---

## 5. Top 10 Gargalos de Performance

| # | Gargalo | Classificação |
|---|---|---|
| 1 | `fetchByCompaniesSequential` — N requests seriais multiselect | P0 |
| 2 | Token WebPosto 2/11 filiais — loops inúteis | P0 |
| 3 | `VENDA_ITEM_REDE` / `LMC_REDE` 401 em massa | P0 |
| 4 | KPIs: 3 chamadas WebPosto síncronas por request | P0 |
| 5 | Agregação multiselect no frontend | P1 |
| 6 | Timeout fuels 30s (vs 90s analytics) | P1 |
| 7 | `fetchDatasetAcrossCompanies` 40 páginas × N empresas | P1 |
| 8 | Executive snapshot collect sequencial por filial | P1 |
| 9 | Ausência cache dedicado LMC | P1 |
| 10 | Paginação KPIs limit=500 sem completude | P1 |

---

## 6. Top 10 Dívidas Técnicas

| # | ID | Problema | Prioridade |
|---|---|---|---|
| 1 | W01 | Token 2/11 filiais combustíveis | P0 |
| 2 | A01 | 8 entrypoints FastAPI | P0 |
| 3 | A02 | 7 clientes WebPosto | P0 |
| 4 | AN01 | Duas fontes litros sem contrato UX | P0 |
| 5 | AN02 | 3 fluxos KPIs executivos divergentes | P0 |
| 6 | AN04 | `VENDA_ITEM_REDE` 401 | P0 |
| 7 | F01 | Agregação multiselect no frontend | P1 |
| 8 | Q01/Q02 | Cobertura 12% + CI falhando | P1 |
| 9 | B01 | Sync logs só memória | P1 |
| 10 | F04 | 14+ dashboards HTML legados | P1 |

---

## 7. Métricas de Maturidade Atualizadas

| Indicador | A02 (1.0) | A02.5 (1.1) | Δ |
|---|---|---|---|
| **Risco arquitetural** | 72/100 | **58/100** | -14 |
| **Nota de maturidade** | 5.5/10 | **6.0/10** | +0.5 |
| Entrypoints mapeados | 8/8 | 8/8 ✅ | — |
| Clientes mapeados | 7/7 | 7/7 ✅ | — |
| Dashboards catalogados | 14 | 21 ✅ | — |
| Plano migração físico | Parcial | Completo ✅ | — |
| Snapshot-first views | 1/7 | 1/7 | A03 alvo 7/7 |

**Nota:** Risco reduzido por plano consolidado aprovado — execução física ainda pendente (A03+).

---

## 8. Ganhos Estimados Pós-Consolidação

| Dimensão | Ganho estimado | Condição |
|---|---|---|
| **Performance carga inicial** | 60-80% | Snapshot-first em todas views (A03) |
| **CPU frontend** | ~40% | Agregação multiselect → backend |
| **Hits WebPosto** | ~70% | Cache LMC dedicado + snapshot |
| **Manutenção** | 30-40% | 1 entrypoint + 1 client + 1 dashboard |
| **Onboarding dev** | ~50% | Estrutura `integrations/` + `analytics/` |

---

## 9. Documentos A02.5 (Entregáveis)

| Documento | Agente | Status |
|---|---|---|
| `ENTRYPOINT_MIGRATION.md` | 1 — Backend | ✅ |
| `WEBPOSTO_CONSOLIDATION_PLAN.md` | 2 — Integração | ✅ |
| `ANALYTICS_CONSOLIDATION_PLAN.md` | 3 — Analytics | ✅ |
| `FUEL_ARCHITECTURE_PLAN.md` | 4 — Combustíveis | ✅ |
| `DASHBOARD_CONSOLIDATION_PLAN.md` | 5 — Frontend | ✅ |
| `TOP_20_PERFORMANCE_BOTTLENECKS.md` | 6 — Performance | ✅ |
| `SNAPSHOT_FIRST_ARCHITECTURE.md` | 7 — Dados | ✅ |
| `TECH_DEBT_MASTER.md` | 8 — Governança | ✅ |
| `ARCHITECTURE_BASELINE_1.1.md` | Orquestrador | ✅ |
| `MIGRATION_PLAN_A02_5.md` | Orquestrador | ✅ |

---

## 10. Roadmap Pós-A02.5

```
A02.5 (agora)  →  A03 Snapshot First  →  A04 Data Warehouse  →  B01..H03 Módulos
     │                    │                      │
     └── 10 docs          └── Fuel snapshot      └── Unificar financial snapshot
         Plano físico         Prewarm startup        Fila persistente refresh
```

---

*Sprint A02.5 — nenhum código alterado. Fundação para A03 Snapshot First.*
