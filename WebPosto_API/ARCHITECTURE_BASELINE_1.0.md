# LOGOS SPACE — Architecture Baseline 1.0
## Sprint A02 — Consolidação Arquitetural e Padronização Oficial

| Campo | Valor |
|---|---|
| **Projeto** | LOGOS SPACE |
| **Sprint** | A02 |
| **Pré-requisito** | `LOGOS_SPACE_COMBUSTIVEIS_BASELINE_1.0.md` (A01.1) |
| **Data** | 2026-06-08 |
| **Escopo** | Consolidação, padronização, planejamento — **sem alteração de código** |
| **Ambiente oficial** | `src/main.py` → porta **8040** → `/app/financial` |

---

## 1. Objetivo Estratégico

Ao final da Sprint A02, o LOGOS SPACE terá:

| Artefato | Status |
|---|---|
| 1 entrada oficial | `src/main.py` |
| 1 cliente WebPosto oficial | `src/gateway/webposto_client.py` |
| 1 engine analytics oficial (por domínio) | Ver §4 |
| 1 catálogo oficial de APIs | `API_CATALOG.md` |
| 1 catálogo oficial de dashboards | `DASHBOARD_CATALOG.md` |
| 1 plano de migração | `MIGRATION_PLAN_A02.md` |

---

## 2. Tabela de EntryPoints

| Arquivo | Responsabilidade | Porta típica | Status Atual | Status Futuro |
|---|---|---|---|---|
| `src/main.py` | **API Financeira LOGOS SPACE** — analytics, enterprise, frontend SPA | 8040 | Ativo, canônico | **OFICIAL** |
| `main.py` (raiz) | Wrapper Docker/CLI → `src.main:app` | 8000 (env) | Ativo | **OFICIAL** (launcher) |
| `src/interfaces/http/app.py` | Factory `create_app()` — monta routers | — | Ativo | **OFICIAL** (factory) |
| `src/presentation/app.py` | Gateway Adelaide — proxy, CRUD legado, UI estática | 8050 (.env) | Ativo, paralelo | **DEPRECATED** (auxiliar até migração) |
| `src/main_minimal.py` | Sync + CRUD legado + enterprise | variável | Inativo em prod | **DEPRECATED** |
| `src/main-mlisboa17.py` | Variante pessoal do desenvolvedor | variável | Inativo | **REMOVER FUTURAMENTE** |
| `logos-webposto-gateway/src/main.py` | Subprojeto gateway duplicado | 8050 | Paralelo | **REMOVER FUTURAMENTE** |
| `explorador_standalone.py` | Explorador técnico WebPosto | variável | Experimental | **REMOVER FUTURAMENTE** |

### Decisão oficial

```
OFICIAL = src/main.py + create_app() + porta 8040
AUXILIAR (transitório) = src/presentation/app.py porta 8050
DEPRECATED = todos os demais entrypoints de produção
```

### Routers montados no entrypoint OFICIAL (8040)

| Router | Prefixo | Arquivo |
|---|---|---|
| health | `/health`, `/ready` | `routes/health.py` |
| fechamento_enterprise | `/v1` | `routes/fechamento_enterprise.py` |
| analytics | `/api/v1` | `routes/analytics.py` |
| gateway_expenses | `/v1/expenses` | `routes/gateway_expenses.py` |
| expenses | `/expenses` | `routes/expenses.py` |
| clientes | `/clientes` | `routes/clientes.py` |
| sync | `/sync` | `routes/sync.py` |
| auth | `/auth` | `routes/auth.py` |
| metrics | `/metrics` | `routes/metrics.py` |
| frontend | `/app/financial` | `app.py` (FileResponse) |

### Routers existentes mas NÃO montados no 8040

| Router | Arquivo | Status Futuro |
|---|---|---|
| auditoria | `routes/auditoria.py` | DEPRECATED (migrar para analytics ou remover) |
| routes_crud | `src/routes_crud.py` | REMOVER FUTURAMENTE |
| audit_routes | `presentation/routes/audit_routes.py` | DEPRECATED (só gateway 8050) |

---

## 3. Engines Analytics Oficiais

| Domínio | Engine Oficial | Arquivo | Engines Depreciadas |
|---|---|---|---|
| **KPI** | `AnalyticsService.get_kpis()` | `services/analytics_service.py` | `fetch_executive_kpis`, `get_executive_metrics`, `metricsEngine.js` (alertas only) |
| **DRE** | `AnalyticsService.get_dre()` | `services/analytics_service.py` | — |
| **Fuel** | `FuelAnalyticsService` + `FuelKpiEngine` | `fuel_analytics_service.py`, `fuel_kpi_engine.py` | `AnalyticsService.get_fuel_summary` (comercial, não físico) |
| **Coverage** | `build_network_coverage()` | `executive_snapshot_service.py` | — |
| **Data Quality** | `DataQualityService` | `data_quality_service.py` | — |
| **Reconciliação** | `FinancialReconciliationEngine` | `financial_reconciliation_engine.py` | Scripts ad-hoc (consolidar) |
| **Snapshot** | `ExecutiveSnapshotService` | `executive_snapshot_service.py` | `FinancialSnapshotService` (HTTP 8041) |

### Regra de ouro — duas métricas de litros

| Métrica | Fonte | Engine | Uso |
|---|---|---|---|
| Litros físicos (LMC) | `CONSULTAR_LMC_REDE` | `FuelAnalyticsService` | Dashboard Combustíveis, snapshot |
| Litros comerciais (vendas) | `VENDA_ITEM` | `AnalyticsService.get_fuel_summary` | Sub-aba Vendas → Combustíveis |

**Não unificar.** Renomear na UI: "Litros LMC" vs "Litros Vendidos".

---

## 4. Arquitetura Snapshot-First (Alvo)

```
┌──────────────┐     fast (≤8s)      ┌─────────────────────┐
│   Frontend   │ ──────────────────► │ /executive/snapshot │
│   SPA 8040   │                     │ /fuel/executive     │
└──────┬───────┘                     │ (cache 60s)         │
       │                             └──────────┬──────────┘
       │ background                           │
       │                             ┌──────────▼──────────┐
       └────────────────────────────►│ POST /executive/     │
                                     │      refresh        │
                                     └──────────┬──────────┘
                                                │
                                     ┌──────────▼──────────┐
                                     │  WebPostoClient     │
                                     │  (background only)  │
                                     └─────────────────────┘
```

| Camada | Atual | Alvo A03+ |
|---|---|---|
| Executive | Snapshot disco + refresh background | Snapshot-first em todas views |
| Combustíveis (`fuels`) | Chamada direta 30s timeout | Cache 60s + snapshot por período |
| Analytics cache | Memória 60s | Memória + Redis opcional |
| Produto catalog | Memória 24h | Memória + disco |
| Sync logs | Memória (perdidos no restart) | SQLite/Postgres |

---

## 5. Estrutura Alvo (12 meses)

```
src/
├── api/                          # ← interfaces/http/routes (renomear)
│   ├── analytics.py
│   ├── enterprise.py             # ← fechamento_enterprise
│   ├── health.py
│   └── ...
├── application/                  # use cases (já existe parcialmente)
│   └── usecases/
├── domain/                       # entities, value objects (já existe)
│   ├── entities/
│   └── governance/
│       └── filial_master.py
├── infrastructure/               # DB, cache, config (já existe)
│   ├── config/
│   └── cache/
├── integrations/               # ← NOVO: consolidar clientes
│   └── webposto/
│       ├── client.py             # ← gateway/webposto_client.py
│       ├── endpoints.py          # mapa ENDPOINTS
│       └── circuit_breaker.py
├── analytics/                  # ← NOVO: consolidar services analytics
│   ├── kpi_engine.py           # ← analytics_service (KPI/DRE)
│   ├── fuel_engine.py          # ← fuel_analytics + fuel_kpi
│   ├── quality_engine.py
│   ├── coverage_engine.py
│   ├── reconciliation_engine.py
│   └── snapshot_service.py
├── workers/                    # background jobs (futuro)
├── governance/                 # FilialMaster, ProdutoCatalog (futuro)
├── frontend/                   # SPA oficial (já na raiz)
└── tests/
```

### Mapa de migração de pastas

| Atual | Alvo |
|---|---|
| `src/gateway/webposto_client.py` | `src/integrations/webposto/client.py` |
| `src/services/analytics_service.py` | `src/analytics/kpi_engine.py` |
| `src/services/fuel_analytics_service.py` | `src/analytics/fuel_engine.py` |
| `src/services/executive_snapshot_service.py` | `src/analytics/snapshot_service.py` |
| `src/interfaces/http/routes/` | `src/api/` |
| `src/domain/entities/filial_master.py` | `src/governance/filial_master.py` |
| `src/services/produto_catalog.py` | `src/governance/produto_catalog.py` |

---

## 6. Top 20 Gargalos de Performance

| # | Gargalo | Classificação | Domínio |
|---|---|---|---|
| 1 | Token WebPosto limita 2/11 filiais — loops por empresa inúteis | ALTO | Integração |
| 2 | `VENDA_ITEM_REDE` retorna 401 — fallback para chamadas individuais | ALTO | Integração |
| 3 | KPIs/DRE fazem 3+ chamadas WebPosto síncronas (expenses, sales, stock) | ALTO | Analytics |
| 4 | `fetchFuelExecutive` timeout 30s vs analytics 90s | ALTO | Frontend |
| 5 | Multiselect empresa: agregação sequencial no frontend (KPIs/DRE) | ALTO | Frontend |
| 6 | `CONSULTAR_LMC_REDE` payload grande em períodos longos | ALTO | Integração |
| 7 | `analise_vendas_combustivel` timeout frequente | ALTO | Integração |
| 8 | Executive refresh sem fila — refresh duplicado possível | MÉDIO | Backend |
| 9 | Paginação KPIs limit=500 — subestima se sem consolidado | MÉDIO | Analytics |
| 10 | `fetchDatasetAcrossCompanies` — até 40 páginas × N empresas | MÉDIO | Frontend |
| 11 | ProdutoCatalog busca PRODUTO por empresa sequencial | MÉDIO | Backend |
| 12 | Sync logs em memória — re-fetch após restart | MÉDIO | Backend |
| 13 | Normalização monetária divergente (analytics vs network) | MÉDIO | Analytics |
| 14 | Gateway 8050 startup chama EMPRESAS 2× no boot | MÉDIO | Integração |
| 15 | `permission_cache` discovery em todos endpoints no boot | MÉDIO | Integração |
| 16 | Coverage endpoint chama `get_companies()` sem cache próprio | MÉDIO | Analytics |
| 17 | `FinancialSnapshotService` usa porta 8041 hardcoded | BAIXO | Scripts |
| 18 | Gráficos CSS inline sem virtualização | BAIXO | Frontend |
| 19 | `pageFuels` na URL não consumido — re-render desnecessário | BAIXO | Frontend |
| 20 | `metrics/executive` conecta Valkey com host hardcoded | BAIXO | Backend |

---

## 7. Documentos Relacionados

| Documento | Conteúdo |
|---|---|
| `WEBPOSTO_CLIENT_ARCHITECTURE.md` | Clientes WebPosto — oficial vs legado |
| `DASHBOARD_CATALOG.md` | Catálogo de dashboards |
| `API_CATALOG.md` | Catálogo completo de rotas |
| `TECH_DEBT_MATRIX.md` | Matriz de dívida técnica |
| `MIGRATION_PLAN_A02.md` | Plano de migração em 5 fases |
| `LOGOS_SPACE_COMBUSTIVEIS_BASELINE_1.0.md` | Baseline A01.1 |

---

## 8. Métricas de Maturidade

| Indicador | Valor | Escala |
|---|---|---|
| **Risco arquitetural** | **72/100** | 0=sem risco, 100=crítico |
| **Nota de maturidade do sistema** | **5.5/10** | Código funcional, arquitetura fragmentada |
| Entrypoints consolidados | 1/8 | |
| Clientes WebPosto consolidados | 1/7 | |
| Dashboards em produção | 1/16 | |
| Cobertura testes | ~12% | |
| Cobertura rede combustíveis | 18% (2/11) | |

---

*Sprint A02 — nenhum código alterado. Apenas consolidação documental.*
