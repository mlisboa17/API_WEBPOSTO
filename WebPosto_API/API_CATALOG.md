# LOGOS SPACE — API Catalog
## Sprint A02 — Catálogo Oficial de Rotas

| Campo | Valor |
|---|---|
| **API oficial** | `src/main.py` → porta **8040** |
| **Prefixos oficiais** | `/api/v1` (analytics), `/v1` (enterprise), `/health` |
| **Data** | 2026-06-08 |

---

## 1. Legenda de Status

| Status | Significado |
|---|---|
| **OFICIAL** | Rota ativa no entrypoint 8040, contrato estável |
| **LEGADO** | Rota ativa mas será substituída ou absorvida |
| **EXPERIMENTAL** | Rota ativa, contrato instável, não usar em produção |
| **DEPRECATED** | Rota existe no código mas não montada no 8040 |
| **GATEWAY** | Rota exclusiva do gateway 8050 (transitório) |

---

## 2. Analytics — `/api/v1` (OFICIAL)

| Rota | Método | Serviço | Status | Substituição futura |
|---|---|---|---|---|
| `/api/v1/kpis` | GET | `AnalyticsService.get_kpis` | **OFICIAL** | — |
| `/api/v1/dre` | GET | `AnalyticsService.get_dre` | **OFICIAL** | — |
| `/api/v1/data-quality` | GET | `DataQualityService` | **OFICIAL** | — |
| `/api/v1/network/coverage` | GET | `build_network_coverage` | **OFICIAL** | — |
| `/api/v1/filiais` | GET | `NetworkFinancialOverviewService` | **OFICIAL** | — |
| `/api/v1/fuel/executive` | GET | `FuelAnalyticsService` + `FuelKpiEngine` | **OFICIAL** | — |
| `/api/v1/sales/fuel-summary` | GET | `AnalyticsService.get_fuel_summary` | **OFICIAL** | Renomear `/fuel/commercial` |
| `/api/v1/products/catalog` | GET | `ProdutoCatalogService` | **OFICIAL** | — |
| `/api/v1/executive/snapshot` | GET | `ExecutiveSnapshotService` | **OFICIAL** | — |
| `/api/v1/executive/refresh` | POST | `ExecutiveSnapshotService` (background) | **OFICIAL** | — |
| `/api/v1/sync/control` | GET | `SyncControlService` | **OFICIAL** | — |
| `/api/v1/sync/logs` | GET | `IntegrationLogService` | **OFICIAL** | Persistir em DB |
| `/api/v1/sync/errors` | GET | `IntegrationLogService` | **OFICIAL** | Persistir em DB |
| `/api/v1/sync/control/{endpoint}/reset` | POST | `SyncControlService` | **OFICIAL** | — |

---

## 3. Enterprise — `/v1` (OFICIAL)

| Rota | Método | Serviço | Status | Substituição futura |
|---|---|---|---|---|
| `/v1/financial/overview` | GET | `NetworkFinancialOverviewService` | **OFICIAL** | — |
| `/v1/financial/companies` | GET | `NetworkFinancialOverviewService` | **OFICIAL** | — |
| `/v1/financial/expenses` | GET | `NetworkFinancialOverviewService` | **OFICIAL** | — |
| `/v1/financial/accounts-payable` | GET | `NetworkFinancialOverviewService` | **OFICIAL** | — |
| `/v1/financial/accounts-receivable` | GET | `NetworkFinancialOverviewService` | **OFICIAL** | — |
| `/v1/sales` | GET | `NetworkFinancialOverviewService` | **OFICIAL** | — |
| `/v1/stock` | GET | `NetworkFinancialOverviewService` | **OFICIAL** | — |
| `/v1/network/financial-overview` | GET | `NetworkFinancialOverviewService` | **OFICIAL** | — |
| `/v1/abastecimento` | GET | `AbastecimentoService` | **OFICIAL** | — |
| `/v1/vendas-combustivel` | GET | `VendasCombustivelService` | **LEGADO** | Absorver em fuel engine |
| `/v1/operacao-inteligente` | GET | `OperacaoInteligenteService` | **LEGADO** | Fase F |
| `/v1/permissions` | GET | `WebPostoClient.discover_permissions` | **OFICIAL** | — |
| `/v1/expenses` | GET | `ExpensesService` | **LEGADO** | Unificar com financial/expenses |
| `/v1/financeiro` | GET | `FinanceiroService` | **LEGADO** | Unificar com accounts-payable |
| `/v1/caixa` | GET | `CaixaService` | **LEGADO** | Fase F |
| `/v1/caixa-apresentado` | GET | `CaixaService` | **LEGADO** | Fase F |
| `/v1/box-closure` | GET | `FechamentoService` | **LEGADO** | Fase F |
| `/v1/observability` | GET | `metrics.collector` | **OFICIAL** | — |

---

## 4. Infraestrutura — 8040

| Rota | Método | Serviço | Status | Substituição futura |
|---|---|---|---|---|
| `/health` | GET | health check | **OFICIAL** | — |
| `/ready` | GET | readiness (DB) | **OFICIAL** | — |
| `/app/financial` | GET | frontend SPA | **OFICIAL** | — |
| `/frontend/*` | GET | StaticFiles | **OFICIAL** | — |
| `/auth/login` | POST | auth mock | **EXPERIMENTAL** | JWT real |
| `/auth/refresh` | POST | auth mock | **EXPERIMENTAL** | JWT real |
| `/auth/logout` | POST | auth mock | **EXPERIMENTAL** | JWT real |
| `/clientes/*` | CRUD | `ClienteService` | **LEGADO** | Fase B04 |
| `/sync/clientes` | POST | `SyncService` | **LEGADO** | Fase B04 |
| `/sync/abastecimentos` | POST | `SyncService` | **LEGADO** | Fase F |
| `/sync/financeiro` | POST | `SyncService` | **LEGADO** | Fase C |
| `/sync/caixa` | POST | `SyncService` | **LEGADO** | Fase F |
| `/sync/full` | POST | `SyncService` | **LEGADO** | Workers |
| `/expenses/extract` | POST | expenses extract | **EXPERIMENTAL** | — |
| `/v1/expenses` (gateway) | GET | `GatewayWebPostoClient` | **LEGADO** | Absorver no oficial |
| `/metrics/executive` | GET | `get_executive_metrics` (Valkey) | **EXPERIMENTAL** | Deprecar → snapshot |
| `/metrics/stream` | GET | SSE stub | **EXPERIMENTAL** | Remover ou implementar |

---

## 5. DEPRECATED — Existem mas NÃO montados no 8040

| Rota | Arquivo | Status | Substituição |
|---|---|---|---|
| `/auditoria/*` | `routes/auditoria.py` | **DEPRECATED** | analytics + reconciliation |
| CRUD `/financeiro/*` | `routes_crud.py` | **DEPRECATED** | enterprise routes |
| `/api/audit/*` | `presentation/routes/audit_routes.py` | **DEPRECATED** | reconciliation engine |

---

## 6. GATEWAY — Exclusivas porta 8050 (transitório)

| Rota | Método | Status | Substituição futura |
|---|---|---|---|
| `/api/v1/adelaide/overview` | GET | **GATEWAY** | executive snapshot |
| `/api/v1/adelaide/metrics` | GET | **GATEWAY** | executive snapshot |
| `/api/v1/adelaide/metrics/async` | POST | **GATEWAY** | executive refresh |
| `/api/v1/proxy/{endpoint}` | GET | **GATEWAY** | WebPostoClient oficial |
| `/api/executive/kpis` | GET | **GATEWAY** | `/api/v1/kpis` |
| `/api/webposto/proxy` | POST | **GATEWAY** | WebPostoClient oficial |
| `/api/v1/dashboard/filtros` | GET | **GATEWAY** | filters.js |
| `/api/v1/webposto/produtos` | GET | **GATEWAY** | `/api/v1/products/catalog` |
| `/dashboard` | GET | **GATEWAY** | `/app/financial` |
| `/produtos` | GET | **GATEWAY** | frontend (futuro) |
| `/app/vendas` | GET | **GATEWAY** | `view=sales` |

---

## 7. Resumo Quantitativo

| Status | Quantidade (8040) | Quantidade (8050) |
|---|---|---|
| OFICIAL | 32 | 0 |
| LEGADO | 12 | 0 |
| EXPERIMENTAL | 6 | 0 |
| DEPRECATED | 8+ | 3+ |
| GATEWAY | 0 | 11 |

---

## 8. Regras Oficiais

1. Novas rotas analytics → prefixo `/api/v1` em `routes/analytics.py`
2. Novas rotas enterprise → prefixo `/v1` em `routes/fechamento_enterprise.py`
3. Proibido criar rotas em `presentation/app.py` (gateway congelado)
4. Toda rota nova → registrar em `API_CATALOG.md`
5. Rotas LEGADO → não recebem features novas

---

*Sprint A02 — catálogo oficial. Sem alteração de código.*
