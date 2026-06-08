# LOGOS SPACE — Baseline Corporativa 1.0
## Módulo: Combustíveis / Postos de Combustíveis

| Campo | Valor |
|---|---|
| **Projeto** | LOGOS SPACE |
| **Módulo** | Combustíveis / Postos de Combustíveis |
| **Ambiente canônico** | API Financeira — `http://127.0.0.1:8040` |
| **Entrypoint** | `src/main.py` → `src/interfaces/http/app.py` |
| **Frontend** | `/app/financial` |
| **Versão baseline** | 1.0 |
| **Data** | 2026-06-08 |
| **Fase** | Encerramento experimental → organização por áreas de negócio |
| **Escopo desta baseline** | Inventário + classificação + planejamento (sem alteração de código) |

---

## 1. Visão Geral

O LOGOS SPACE é uma plataforma de inteligência operacional e financeira para rede de postos de combustíveis. O módulo **Combustíveis** integra dados do WebPosto (Quality Automação) com governança corporativa local (FilialMaster, ProdutoCatalog) e camadas analíticas (KPIs, DRE, LMC, snapshots).

**Estado atual:** funcional para **2 filiais** (POSTO VIP 11495 e AP CASA CAIADA 5555) com cobertura parcial de rede. O sistema possui múltiplos entrypoints, dashboards legados e duas fontes de litros (LMC vs VENDA_ITEM) que coexistem sem unificação formal.

**Ambiente de trabalho oficial a partir desta baseline:** API Financeira porta **8040**, frontend SPA em `/app/financial`.

---

## 2. Arquitetura Atual

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend SPA (frontend/)                                       │
│  /app/financial?view=executive|fuels|sales|dashboard|...        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP
┌───────────────────────────▼─────────────────────────────────────┐
│  src/main.py → src/interfaces/http/app.py  [PORTA 8040]        │
│  ├── analytics.router        (/api/v1/*)                        │
│  ├── fechamento_enterprise   (/v1/financial/*, /v1/sales, ...)  │
│  ├── health, auth, clientes, sync, metrics, gateway_expenses    │
│  └── GET /app/financial → frontend/index.html                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  Services Layer      Caches/Snapshots     WebPostoClient
  (fuel, analytics,   (analytics 60s,      (Quality API)
   produto, network)  produto 24h,
                      executive JSON)
```

**Entrypoints paralelos (não canônicos para Combustíveis 8040):**

| Entrypoint | Porta | Escopo |
|---|---|---|
| `src/presentation/app.py` | 8050 (.env) | Gateway Adelaide, proxy, UI legada |
| `src/main_minimal.py` | variável | CRUD legado + sync |
| `logos-webposto-gateway/` | 8050 | Subprojeto gateway separado |
| ~20 HTML dashboards legados | estático | Protótipos experimentais |

---

## 3. Módulos Existentes

| Módulo | Backend | Frontend | Status geral |
|---|---|---|---|
| Governança | FilialMaster, ProdutoCatalog | filiais.js, filters | **PRONTO** (local) |
| Financeiro | fechamento_enterprise | dashboard, expenses, accounts | **PARCIAL** |
| Estoque | /v1/stock | stock.js | **PARCIAL** |
| Vendas | /v1/sales | sales.js | **PARCIAL** |
| **Combustíveis** | fuel/executive, fuel-summary | fuels, sales/fuels, executive card | **PARCIAL** |
| Operação | abastecimento, LMC, tanques | dashboards legados | **EXPERIMENTAL** |
| Gestão | executive snapshot, KPIs, DRE | executiveDashboard | **PARCIAL** |
| Integrações | WebPostoClient, sync logs | api.js, apiClient | **PARCIAL** |
| Analytics | analytics.py (14 rotas) | analyticsEngine, metricsEngine | **PARCIAL** |

---

## 4. Backend

### 4.1 Rotas — LOGOS SPACE Analytics (`/api/v1`)

| Rota | Serviço | Classificação |
|---|---|---|
| `GET /kpis` | AnalyticsService | PRONTO |
| `GET /dre` | AnalyticsService | PRONTO |
| `GET /data-quality` | DataQualityService | PRONTO |
| `GET /network/coverage` | build_network_coverage | PRONTO |
| `GET /filiais` | NetworkFinancialOverviewService | PRONTO |
| `GET /sales/fuel-summary` | AnalyticsService (VENDA_ITEM) | PARCIAL |
| `GET /fuel/executive` | FuelAnalyticsService (LMC_REDE) | PRONTO |
| `GET /products/catalog` | ProdutoCatalogService | PRONTO |
| `GET /executive/snapshot` | ExecutiveSnapshotService | PRONTO |
| `POST /executive/refresh` | ExecutiveSnapshotService (background) | PARCIAL |
| `GET /sync/control` | SyncControlService | PRONTO |
| `GET /sync/logs` | IntegrationLogService | PRONTO |
| `GET /sync/errors` | IntegrationLogService | PRONTO |
| `POST /sync/control/{endpoint}/reset` | SyncControlService | PRONTO |

### 4.2 Rotas — Enterprise (`/v1`)

| Rota | Classificação | Relevância combustíveis |
|---|---|---|
| `GET /v1/financial/overview` | PRONTO | Indireta |
| `GET /v1/financial/companies` | PRONTO | Governança filiais |
| `GET /v1/financial/expenses` | PRONTO | DRE/KPIs |
| `GET /v1/financial/accounts-payable` | PRONTO | Alertas executive |
| `GET /v1/sales` | PRONTO | Vendas detalhadas |
| `GET /v1/stock` | PRONTO | KPI estoque |
| `GET /v1/abastecimento` | PRONTO | Operação |
| `GET /v1/vendas-combustivel` | PARCIAL | Análise combustível |
| `GET /v1/operacao-inteligente` | PARCIAL | Visão unificada |

### 4.3 Serviços

| Arquivo | Função | Classificação |
|---|---|---|
| `fuel_analytics_service.py` | Litros via LMC_REDE | PRONTO |
| `fuel_kpi_engine.py` | KPIs derivados (líder, % diesel/gasolina/etanol) | PRONTO |
| `analytics_service.py` | KPIs, DRE, fuel-summary | PRONTO / PARCIAL |
| `produto_catalog.py` | Catálogo unificado, flag combustível | PRONTO |
| `network_financial_overview_service.py` | Orquestração rede financeira | PRONTO |
| `executive_snapshot_service.py` | Snapshot JSON disco+memória | PRONTO |
| `data_quality_service.py` | Score qualidade dados | PRONTO |
| `analytics_cache.py` | Cache in-memory TTL 60s | PRONTO |
| `money_normalizer.py` | Normalização monetária BR | PRONTO |
| `sync_control_service.py` | Sync state + logs (memória) | PRONTO |
| `vendas_combustivel_service.py` | Análise vendas combustível | PARCIAL |
| `financial_snapshot_service.py` | Snapshot HTTP legado | EXPERIMENTAL |
| `financial_reconciliation_engine.py` | Reconciliação scripts | PARCIAL |

### 4.4 Workers / Background

| Componente | Classificação | Observação |
|---|---|---|
| `executive_snapshot_service` refresh | PARCIAL | asyncio.create_task, sem fila persistente |
| Celery stubs (`tasks.py`) | EXPERIMENTAL | Não conectado |
| Adelaide background jobs | EXPERIMENTAL | Só gateway 8050 |

### 4.5 Caches

| Cache | TTL | Escopo |
|---|---|---|
| `analytics_cache` | 60s | KPIs, DRE, fuel, data-quality |
| `ProdutoCatalogService` | 24h | Catálogo produtos |
| `permission_cache` | configurável | Permissões WebPosto |
| Executive snapshot (disco) | persistente | `snapshots/executive/*.json` |

### 4.6 Rotas não montadas na API 8040

| Arquivo | Classificação |
|---|---|
| `routes/auditoria.py` | OBSOLETO (8040) |
| `routes_crud.py` | OBSOLETO (8040) |
| `presentation/routes/audit_routes.py` | OBSOLETO (8040) |

---

## 5. Frontend

### 5.1 Telas

| View (`?view=`) | Arquivo | Classificação |
|---|---|---|
| `executive` | `executiveDashboard.js` | PARCIAL |
| `fuels` | `fuelExecutiveDashboard.js` | PRONTO |
| `sales` → subtab fuels | `sales.js` | PRONTO |
| `dashboard` | `dashboard.js` | PARCIAL |
| `expenses` | `expenses.js` | PARCIAL |
| `accounts` | `accountsPayable.js` | PARCIAL |
| `stock` | `stock.js` | PARCIAL |

### 5.2 Componentes

| Componente | Uso em combustíveis |
|---|---|
| `filters.js` | Data, empresa (multiselect) |
| `table.js` | Tabela fuels + export CSV/PDF |
| `filiais.js` | FilialMaster espelho (12 filiais) |
| `productCatalog.js` | Enriquecimento nomes combustível |
| `api.js` / `apiClient.js` | HTTP + timeouts |
| `export.js` | CSV/PDF |

### 5.3 Filtros disponíveis vs suportados

| Filtro | UI | API suporta |
|---|---|---|
| dataInicial / dataFinal | Sim | Sim |
| empresaCodigo (multiselect) | Sim | Sim |
| combustivel / filial | **Não** | Sim (parâmetros existem) |
| centroCusto / tipoDespesa | Sim (global) | Sim |

### 5.4 Exportações

| View | Formatos | Nome arquivo |
|---|---|---|
| Combustíveis (`fuels`) | CSV, PDF | `executivo_combustiveis_{data}` |
| Vendas → Combustíveis | CSV, PDF | `comercial_combustiveis_{data}` |
| Executive card fuels | **Nenhum** | — |

### 5.5 Timeouts frontend

| Endpoint | Timeout |
|---|---|
| `/api/v1/fuel/executive` | 30s |
| `/api/v1/sales/fuel-summary` | 30s |
| `/api/v1/executive/snapshot` | 8s |
| `/api/v1/executive/refresh` | 5s |
| `/api/v1/kpis`, `/dre` | 90s |
| `/api/v1/network/coverage` | 45s |

---

## 6. Integrações WebPosto

### 6.1 Endpoints utilizados para combustíveis

| Endpoint WebPosto | Uso | Status token atual |
|---|---|---|
| `/INTEGRACAO/CONSULTAR_LMC_REDE` | **Fonte oficial** fuel/executive | HTTP 200 — 2 filiais |
| `/INTEGRACAO/VENDA_ITEM` | fuel-summary (por empresa) | HTTP 200 — 2 filiais |
| `/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE` | KPIs/DRE lineage | **401 bloqueado** |
| `/INTEGRACAO/PRODUTO` | Nomes/categorias | HTTP 200 |
| `/INTEGRACAO/PRODUTO_EMPRESA` | Catálogo por empresa | HTTP 200 |
| `/INTEGRACAO/PRODUTO_COMBUSTIVEL` | Mapeado, pouco usado | **401** |
| `/INTEGRACAO/CONSULTAR_ANALISE_VENDAS_COMBUSTIVEL` | vendas-combustivel | Timeout risk |
| `/INTEGRACAO/ABASTECIMENTO` | Abastecimento unitário | HTTP 200 |
| `/INTEGRACAO/EMPRESAS` | Resolução filiais | HTTP 200 — 2 filiais |
| `/INTEGRACAO/PRODUTO_ESTOQUE` | KPI estoque | HTTP 200 parcial |
| `/INTEGRACAO/TANQUE` | Tanques | HTTP 200 — 2 filiais |

### 6.2 Matriz de status

| Status | Endpoints |
|---|---|
| **HTTP 200 com dados** | DESPESAS_REDE (10 filiais), LMC_REDE (2), CAIXA_REDE (2), TANQUE (2), PRODUTO, ABASTECIMENTO |
| **HTTP 200 vazio** | TITULO_PAGAR_REDE, CAIXA_APRESENTADO_REDE |
| **HTTP 401** | VENDA_ITEM_REDE, VENDA_REDE, ABASTECIMENTO_REDE, PRODUTO_COMBUSTIVEL, PRODUTO_EMPRESA_REDE |
| **Timeout** | analise_vendas_combustivel, estoque_periodo (períodos longos) |

### 6.3 Cobertura por filial (11 ativas + 1 inativa)

| Domínio | Filiais com dados | % |
|---|---|---|
| Despesas rede | 10/11 | 91% |
| LMC / Combustíveis | 2/11 | 18% |
| Vendas | 2/11 | 18% |
| Estoque | 2/11 | 18% |
| Caixa rede | 2/11 | 18% |

---

## 7. Governança

### 7.1 FilialMaster

- **Fonte:** `src/domain/entities/filial_master.py`
- **12 filiais** cadastradas (11 CONFIRMADA + 1 INATIVA: POSTO REAL)
- 1 PENDENTE_IDENTIFICACAO (AUTO POSTO GLOBO — sem codWeb)
- **Espelho frontend:** `frontend/components/filiais.js`
- **Classificação:** PRONTO
- **Cobertura operacional:** PARCIAL (token limita dados a 2 filiais)

### 7.2 ProdutoCatalog

- **Backend:** `src/services/produto_catalog.py` — cache 24h, 417 produtos
- **Frontend:** `frontend/services/productCatalog.js`
- Flag `combustivel`, resolução `combustivelDisplay`
- **Classificação:** PRONTO

### 7.3 Funcionários

- Campo `funcionarioCodigo` em payloads de venda
- Endpoint `/INTEGRACAO/VALE_FUNCIONARIO_REDE` bloqueado (401)
- Sem serviço dedicado, sem CRUD, sem sync
- **Classificação:** NAO VALIDADA

### 7.4 Clientes

- Duas implementações: `cliente_service` (limpo) vs `crud.py` (legado)
- `/clientes/` retorna 500 em auditoria (DB)
- **Classificação:** PARCIAL / BAIXA confiabilidade

---

## 8. Financeiro

| Funcionalidade | Backend | Frontend | Status |
|---|---|---|---|
| Overview financeiro | `/v1/financial/overview` | dashboard.js | PARCIAL |
| Despesas | `/v1/financial/expenses` | expenses.js | PRONTO |
| Contas a pagar | `/v1/financial/accounts-payable` | accountsPayable.js | PRONTO |
| Contas a receber | `/v1/financial/accounts-receivable` | — | PARCIAL |
| DRE gerencial | `/api/v1/dre` | executiveDashboard | PRONTO (código) |
| KPIs | `/api/v1/kpis` | executiveDashboard | PRONTO (código) |
| Reconciliação BI | scripts + engine | debug mode | BAIXA |
| Conciliação bancária | — | — | NAO INICIADA |
| Fluxo de caixa | — | — | NAO INICIADA |

---

## 9. Estoque

| Funcionalidade | Status |
|---|---|
| Consulta estoque (`/v1/stock`) | PARCIAL (2/11 filiais) |
| KPI estoque total (analytics) | PARCIAL |
| Custo médio | NAO INICIADA |
| Sugestão de compras | NAO INICIADA |
| Ruptura | NAO INICIADA |
| Alteração de preços | EXPERIMENTAL (scripts CRUD) |

---

## 10. Vendas

| Funcionalidade | Status |
|---|---|
| Vendas paginadas (`/v1/sales`) | PARCIAL |
| Vendas por item / forma pagamento | PARCIAL |
| Sub-aba Combustíveis (comercial) | PRONTO |
| Vendas por funcionário | NAO INICIADA |
| Vendas por turno | NAO INICIADA |
| Vendas por cliente | NAO INICIADA |
| Ticket médio (KPI) | PRONTO (código) |

---

## 11. Combustíveis

### 11.1 Funcionalidades atuais

| Funcionalidade | Fonte de dados | Status |
|---|---|---|
| Dashboard executivo combustíveis (`/api/v1/fuel/executive`) | LMC_REDE | PRONTO (2 filiais) |
| Resumo comercial (`/api/v1/sales/fuel-summary`) | VENDA_ITEM | PARCIAL |
| KPIs: litros, líder combustível, líder filial, % diesel/gasolina/etanol | FuelKpiEngine | PRONTO |
| Gráficos: barras, pizza, ranking Top 10 | fuelExecutiveDashboard.js | PRONTO |
| Tabela detalhe filial × combustível | fuelExecutiveDashboard.js | PRONTO |
| Export CSV/PDF | export.js | PRONTO |
| Card mix combustíveis no Painel Executivo | executive snapshot | PARCIAL |
| Enriquecimento nomes via catálogo | productCatalog.js | PRONTO |
| Aviso cobertura parcial (5555, 11495) | UI hardcoded | PRONTO |

### 11.2 Duplicidade crítica — duas fontes de litros

| Rota | Fonte | Significado |
|---|---|---|
| `/api/v1/fuel/executive` | LMC_REDE | Litros físicos (saída LMC) |
| `/api/v1/sales/fuel-summary` | VENDA_ITEM | Litros comerciais (faturados) |

**Os números não são garantidamente iguais.** Snapshot executivo usa LMC.

### 11.3 Confiabilidade analytics combustíveis

| Métrica | Confiabilidade |
|---|---|
| Litros LMC (5555, 11495) | ALTA |
| Litros rede completa | BAIXA (2/11) |
| Mix combustíveis (%) | ALTA (filiais com LMC) |
| Faturamento combustível | MEDIA |
| Reconciliação LMC vs Vendas | NAO VALIDADA |

---

## 12. Operação

| Funcionalidade | Status |
|---|---|
| LMC (CONSULTAR_LMC_REDE) | PRONTO (2 filiais) |
| Abastecimento individual | PRONTO |
| Tanques (TANQUE) | PARCIAL (2 filiais) |
| Bombas / Bicos | NAO INICIADA |
| Perdas | NAO INICIADA |
| Caixa rede | PARCIAL (2 filiais) |
| Dashboards legados abastecimento | EXPERIMENTAL |

---

## 13. Gestão

| Funcionalidade | Status |
|---|---|
| Painel Executivo | PARCIAL (snapshot + fallback) |
| DRE Gerencial | PRONTO (código) |
| Margem % | PRONTO (código) |
| Ranking filiais (Top N) | PARCIAL (client-side) |
| Score operacional rede | PARCIAL (network/coverage) |
| Alertas automáticos | PARCIAL (client-side) |
| Qualidade dos dados | PRONTO (código) |

---

## 14. Analytics

| Componente | Confiabilidade | Observação |
|---|---|---|
| KPIs backend | MEDIA | VENDA_ITEM_REDE bloqueado; usa fallback |
| DRE backend | MEDIA | Validação matemática ok; dados parciais |
| Fuel Analytics (LMC) | ALTA (2 filiais) / BAIXA (rede) | Validado Sprint 23 |
| Network Coverage | MEDIA | Lógica ok; dados subjacentes parciais |
| Data Quality | MEDIA | 7 testes unitários |
| Executive Snapshot | MEDIA | Disco + background refresh |
| Reconciliação financeira | BAIXA | Timeouts em cadeia |
| Fuel-summary (vendas) | BAIXA | Sem dados rede |

---

## 15. QA

### 15.1 Testes automatizados

| Categoria | Quantidade | Estado |
|---|---|---|
| Unit tests | ~200 funções | ~12% cobertura |
| Integration (WebPosto real) | 4+ arquivos | Requer API_KEY |
| Executive snapshot smoke | `test_executive_snapshot.py` | PRONTO |

### 15.2 Scripts de auditoria

| Script | Domínio |
|---|---|
| `fuel_network_audit.py` | Cobertura LMC rede |
| `webposto_endpoint_audit.py` | Rotas locais |
| `audit_filial_master.py` | FilialMaster × API |
| `financial_reconciliation_audit.py` | Reconciliação BI |
| `scripts/test_executive_snapshot.py` | Snapshot executivo |

### 15.3 Evidências documentadas

- `fuel_dashboard_validation.md` — UI combustíveis validada
- `fuel_network_audit_report.md` — 2/10 filiais LMC
- `SPRINT_23_RELATORIO_FINAL.md` — 8/10 itens OK
- `SPRINT_21_3_AUDITORIA_ENDPOINTS_WEBPOSTO.md` — ABERTA

### 15.4 Bugs críticos conhecidos

| Bug | Impacto | Status |
|---|---|---|
| Token limita 8 filiais em vendas/LMC | Dashboard rede incompleto | **Bloqueador externo** |
| VENDA_ITEM_REDE retorna 401 | KPIs/DRE rede imprecisos | **Bloqueador externo** |
| Duas fontes de litros sem documentação UX | Confusão LMC vs vendas | Aberto |
| `fetchFuelExecutive` timeout 30s | Falha em períodos longos | Aberto |
| Reconciliação financeira com timeout | Critério aceite não atingido | Aberto |
| Múltiplos entrypoints FastAPI | Confusão operacional | Aberto |
| Sync `/sync/*` retorna 500 | Sync automático inoperante | Aberto |
| `pageFuels` na URL não consumido | UX inconsistente | Menor |
| `refreshSalesOnly` não re-enriquece catálogo | Nomes degradados | Menor |

---

## 16. Dívidas Técnicas

### ALTA

| Item | Domínio |
|---|---|
| Múltiplos entrypoints FastAPI (4+) | Arquitetura |
| 4+ clientes WebPosto paralelos | Integrações |
| Token Quality limita cobertura rede | Integrações |
| Duas fontes de litros sem contrato unificado | Analytics |
| Normalização monetária divergente (analytics vs network) | Backend |
| ~20 dashboards HTML legados coexistindo | Frontend |

### MEDIA

| Item | Domínio |
|---|---|
| Auditoria endpoint classifica 422 como OBSOLETO | QA |
| Cobertura testes ~12% | QA |
| Sync logs só em memória (perdidos no restart) | Backend |
| Multiselect empresa: agregação no frontend | Frontend |
| Paginação KPIs limit=500 | Performance |
| Executive refresh sem fila persistente | Backend |
| Auth mock / JWT não validado | Segurança |

### BAIXA

| Item | Domínio |
|---|---|
| `pageFuels` não consumido | Frontend |
| Gráficos CSS inline (sem lib charts) | Frontend |
| `window.salesActiveSubview` não na URL | Frontend |
| Celery stubs não conectados | Backend |
| `metrics/stream` SSE stub | Backend |

---

## 17. Funcionalidades Prontas

- Dashboard Combustíveis (`view=fuels`) — KPIs, gráficos, tabela, export
- Sub-aba Vendas → Combustíveis — visão comercial
- `GET /api/v1/fuel/executive` — LMC com FuelKpiEngine
- `GET /api/v1/products/catalog` — 417 produtos, cache 24h
- FilialMaster — 12 filiais governança local
- Enriquecimento nomes combustível via catálogo
- Despesas rede — 10 filiais
- Executive snapshot leitura (`/executive/snapshot`)
- DRE/KPIs backend (código + lineage)
- Data quality score
- Network coverage report
- Export CSV/PDF tabelas fuels

---

## 18. Funcionalidades Parciais

- Painel Executivo (snapshot + refresh background)
- Card mix combustíveis no executive
- `sales/fuel-summary` (só 2 filiais)
- Cobertura rede combustíveis (2/11)
- Vendas/estoque rede (2/11)
- Multiselect empresa (agregação frontend)
- Reconciliação financeira
- Clientes CRUD
- Sync automático
- Operação inteligente
- Filtros combustível/filial (API sim, UI não)

---

## 19. Funcionalidades Não Iniciadas

- Conciliação bancária
- Conciliação de cartões
- Fluxo de caixa
- Custo médio estoque
- Sugestão de compras
- Ruptura estoque
- Vendas por funcionário / turno / cliente
- Gestão bombas / bicos
- Perdas operacionais
- LMC completo rede
- Forecast combustíveis
- IA operacional
- Data Warehouse
- Funcionários (módulo completo)

---

## 20. Roadmap

### FASE A — FUNDAÇÃO

| Sprint | Objetivo | Status |
|---|---|---|
| A01 | Inventário e Baseline | **EM CURSO** (este documento) |
| A02 | Reorganização Arquitetural | Planejado |
| A03 | Executive Snapshot | **Implementado** (parcial) |
| A04 | Data Warehouse Inicial | Não iniciado |

### FASE B — GOVERNANÇA

| Sprint | Objetivo |
|---|---|
| B01 | Filiais — expandir cobertura token |
| B02 | Produtos — unificar catálogo combustível |
| B03 | Funcionários |
| B04 | Clientes — consolidar CRUD |

### FASE C — FINANCEIRO

| Sprint | Objetivo |
|---|---|
| C01 | Despesas |
| C02 | Contas a Pagar |
| C03 | Extratos Bancários |
| C04 | Conciliação Bancária |
| C05 | Conciliação de Cartões |
| C06 | Fluxo de Caixa |

### FASE D — ESTOQUE

| Sprint | Objetivo |
|---|---|
| D01 | Estoque |
| D02 | Custo Médio |
| D03 | Sugestão de Compras |
| D04 | Ruptura |
| D05 | Alteração de Preços |

### FASE E — VENDAS

| Sprint | Objetivo |
|---|---|
| E01 | **Combustíveis** (prioridade) |
| E02 | Vendas por Funcionário |
| E03 | Vendas por Turno |
| E04 | Vendas por Cliente |
| E05 | Ticket Médio |

### FASE F — OPERAÇÃO

| Sprint | Objetivo |
|---|---|
| F01 | LMC |
| F02 | Tanques |
| F03 | Bombas |
| F04 | Bicos |
| F05 | Perdas |

### FASE G — GESTÃO

| Sprint | Objetivo |
|---|---|
| G01 | Executive Dashboard |
| G02 | DRE Gerencial |
| G03 | Margem |
| G04 | Ranking |
| G05 | Score Operacional |

### FASE H — INTELIGÊNCIA

| Sprint | Objetivo |
|---|---|
| H01 | Alertas |
| H02 | Forecast |
| H03 | IA Operacional |

---

## 21. Reorganização por Negócio

### A. Governança

| Campo | Conteúdo |
|---|---|
| **Objetivo** | Fonte única de verdade para filiais, produtos, pessoas e clientes |
| **Atual** | FilialMaster (12), ProdutoCatalog (417), clientes duplicado, funcionários ausente |
| **Faltante** | Token multi-filial, funcionários, clientes consolidado, Globo identificado |
| **Prioridade** | **ALTA** |

### B. Financeiro

| Campo | Conteúdo |
|---|---|
| **Objetivo** | Visão financeira consolidada da rede |
| **Atual** | Despesas (10 filiais), contas, DRE, KPIs |
| **Faltante** | Conciliação, fluxo de caixa, extratos, cartões |
| **Prioridade** | **ALTA** |

### C. Estoque

| Campo | Conteúdo |
|---|---|
| **Objetivo** | Controle de estoque e custos |
| **Atual** | Consulta básica (2 filiais) |
| **Faltante** | Custo médio, ruptura, sugestão compras |
| **Prioridade** | **MÉDIA** |

### D. Vendas

| Campo | Conteúdo |
|---|---|
| **Objetivo** | Análise comercial por produto, funcionário, turno |
| **Atual** | Vendas paginadas, sub-aba combustíveis |
| **Faltante** | Vendas rede completa, por funcionário/turno/cliente |
| **Prioridade** | **ALTA** |

### E. Combustíveis (módulo focal)

| Campo | Conteúdo |
|---|---|
| **Objetivo** | Inteligência de litros, mix, margem e operação de combustíveis |
| **Atual** | fuel/executive (LMC), fuel-summary (vendas), dashboard completo (2 filiais) |
| **Faltante** | Cobertura 11 filiais, unificação LMC vs vendas, LMC completo, tanques/bombas |
| **Prioridade** | **CRÍTICA** |

### F. Operação

| Campo | Conteúdo |
|---|---|
| **Objetivo** | Controle operacional de posto (LMC, tanques, bombas, perdas) |
| **Atual** | LMC parcial, abastecimento, tanques (2 filiais) |
| **Faltante** | Bombas, bicos, perdas, operação rede |
| **Prioridade** | **MÉDIA** |

### G. Gestão

| Campo | Conteúdo |
|---|---|
| **Objetivo** | Painel executivo para tomada de decisão |
| **Atual** | Executive dashboard com snapshot, KPIs, DRE, alertas |
| **Faltante** | Dados rede completa, ranking confiável, score operacional |
| **Prioridade** | **ALTA** |

### H. Integrações

| Campo | Conteúdo |
|---|---|
| **Objetivo** | Camada única de integração WebPosto |
| **Atual** | WebPostoClient (gateway), sync logs, permission cache |
| **Faltante** | Token expandido, endpoints _REDE liberados, sync persistente |
| **Prioridade** | **CRÍTICA** |

### I. Analytics

| Campo | Conteúdo |
|---|---|
| **Objetivo** | BI auditável com lineage e reconciliação |
| **Atual** | KPIs, DRE, data quality, fuel analytics, snapshots |
| **Faltante** | Reconciliação confiável, DW, forecast |
| **Prioridade** | **ALTA** |

---

## Apêndice A — Top 10 Melhorias de Performance

1. Unificar timeout fuels (30s → 90s alinhado com analytics)
2. Cache LMC por filial+período (TTL 5–15 min)
3. Snapshot pré-aquecido no startup para período default
4. Paginação server-side na tabela fuels (evitar payload gigante)
5. Reduzir chamadas sequenciais multiselect (agregar no backend)
6. Persistir sync logs em SQLite/Postgres (evitar re-fetch)
7. Circuit breaker tuning para endpoints _REDE
8. CDN/cache estático para frontend assets
9. Compressão gzip já ativa — validar em todos entrypoints
10. Background refresh com fila (evitar refresh duplicado)

## Apêndice B — Top 10 Melhorias de Arquitetura

1. Entry point único (`src/main.py` canônico, deprecar presentation como gateway separado)
2. Cliente WebPosto único (eliminar 4 implementações)
3. Contrato formal LMC vs VENDA_ITEM (duas métricas, nomes distintos na UI)
4. Consolidar dashboards legados → frontend SPA
5. Mover agregação multiselect para backend
6. Sync logs persistentes
7. Separar config portas (8040 financeiro, 8050 gateway) explicitamente
8. Deprecar routes_crud e auditoria não montados
9. OpenAPI único gerado e validado por contract_check.js
10. Filas de background (Redis/Celery) para refresh e sync

## Apêndice C — Top 10 Oportunidades de Negócio

1. Dashboard combustíveis rede completa (11 postos)
2. Comparativo mix combustível entre filiais
3. Margem por combustível (litro × preço − custo)
4. Ranking operacional de filiais por litros
5. Alertas de queda de volume por filial
6. Integração LMC × estoque tanques
7. Análise sazonal de combustíveis (forecast)
8. Score de saúde operacional por posto
9. Conciliação abastecimento × vendas
10. Relatório executivo PDF automatizado para diretoria

## Apêndice D — Top 10 Riscos do Projeto

1. **Token WebPosto limitado** — bloqueia 82% da rede em combustíveis
2. **Duas fontes de litros** — decisões baseadas em métricas diferentes
3. **Múltiplos entrypoints** — equipe usa app errado
4. **Reconciliação não validada** — números financeiros podem divergir
5. **Cobertura testes 12%** — regressões não detectadas
6. **Sync em memória** — perda de telemetria no restart
7. **Dashboards legados** — confusão sobre qual é oficial
8. **Dependência Quality Automação** — sem SLA formal
9. **Dados POSTO REAL inativo** — filial fora da operação mas no master
10. **AUTO POSTO GLOBO pendente** — buraco na governança

---

*Documento gerado pelo processo A01 — Inventário e Baseline. Nenhum código foi alterado.*
