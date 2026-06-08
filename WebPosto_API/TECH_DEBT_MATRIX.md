# LOGOS SPACE — Technical Debt Matrix
## Sprint A02 — Matriz de Dívida Técnica

| Campo | Valor |
|---|---|
| **Data** | 2026-06-08 |
| **Base** | A01.1 Baseline + A02 Consolidação |

---

## Legenda

| Prioridade | Significado |
|---|---|
| P0 | Bloqueador — resolver antes de novas features |
| P1 | Alto — resolver em 1-2 sprints |
| P2 | Médio — resolver em 3-6 sprints |
| P3 | Baixo — backlog |

| Esforço | Significado |
|---|---|
| XS | < 1 dia |
| S | 1-3 dias |
| M | 1-2 semanas |
| L | 2-4 semanas |
| XL | > 1 mês |

---

## 1. Arquitetura

| # | Problema | Impacto | Prioridade | Esforço |
|---|---|---|---|---|
| A01 | 8 entrypoints FastAPI coexistindo | Equipe usa app errado, bugs de rota | P0 | M |
| A02 | 7 clientes WebPosto paralelos | Comportamento inconsistente, manutenção 7× | P0 | L |
| A03 | Gateway 8050 duplica rotas do 8040 | KPIs em 3 fluxos diferentes | P1 | L |
| A04 | Subprojeto `logos-webposto-gateway/` duplicado | Confusão de deploy | P2 | M |
| A05 | Estrutura `src/` não reflete domínios de negócio | Onboarding lento | P2 | L |
| A06 | `routes_crud.py` + `auditoria.py` órfãos | Código morto aparente ativo | P2 | S |
| A07 | `main-mlisboa17.py` variante pessoal no repo | Risco de deploy acidental | P3 | XS |

---

## 2. Backend

| # | Problema | Impacto | Prioridade | Esforço |
|---|---|---|---|---|
| B01 | Sync logs só em memória (1000 entradas) | Perda de telemetria no restart | P1 | M |
| B02 | Executive refresh sem fila persistente | Refresh duplicado, race conditions | P1 | M |
| B03 | Paginação KPIs limit=500 sem garantia | Subestimação de faturamento | P1 | M |
| B04 | Normalização monetária divergente (2 implementações) | Reconciliação falha | P1 | M |
| B05 | Auth mock (JWT não validado) | Segurança inexistente | P2 | L |
| B06 | `/sync/*` retorna 500 (DB não inicializado) | Sync automático inoperante | P2 | M |
| B07 | `/clientes/` retorna 500 em auditoria | CRUD clientes quebrado | P2 | M |
| B08 | Celery tasks são stubs | Background jobs não funcionam | P3 | L |
| B09 | `metrics/executive` Valkey host hardcoded | Falha se Valkey indisponível | P3 | S |

---

## 3. Frontend

| # | Problema | Impacto | Prioridade | Esforço |
|---|---|---|---|---|
| F01 | Multiselect empresa agrega no frontend | Divergência com backend, lento | P1 | M |
| F02 | `fetchFuelExecutive` timeout 30s (vs 90s analytics) | Timeout em períodos longos | P1 | S |
| F03 | Executive fuels sem fallback direto se snapshot null | Card vazio sem dados | P1 | S |
| F04 | 14 dashboards HTML legados coexistindo | Confusão de qual usar | P1 | M |
| F05 | `window.salesActiveSubview` não na URL | Estado perdido no refresh | P2 | XS |
| F06 | `pageFuels` persistido mas não consumido | Código morto | P3 | XS |
| F07 | `refreshSalesOnly` não re-enriquece catálogo | Nomes degradados | P2 | S |
| F08 | Gráficos CSS inline sem lib charts | Limitação visual, manutenção | P3 | M |

---

## 4. Analytics

| # | Problema | Impacto | Prioridade | Esforço |
|---|---|---|---|---|
| AN01 | Duas fontes de litros (LMC vs VENDA_ITEM) sem contrato UX | Decisões com métricas diferentes | P0 | S |
| AN02 | 3 fluxos de KPIs executivos (analytics, Adelaide, metrics) | Números divergentes | P0 | M |
| AN03 | Reconciliação financeira com timeout em cadeia | Critério aceite não atingido | P1 | L |
| AN04 | `VENDA_ITEM_REDE` bloqueado (401) | KPIs rede imprecisos | P0 | XS* |
| AN05 | Coverage sem cache próprio | Chamada companies a cada request | P2 | S |
| AN06 | `FinancialSnapshotService` porta 8041 hardcoded | Script quebrado se porta muda | P3 | XS |

*AN04 depende de ação externa (Quality Automação).

---

## 5. Integração

| # | Problema | Impacto | Prioridade | Esforço |
|---|---|---|---|---|
| I01 | Token WebPosto limita 2/11 filiais em combustíveis | Dashboard rede 18% cobertura | P0 | XS* |
| I02 | Endpoints `_REDE` retornam 401 em massa | Força loop por empresaCodigo | P0 | XS* |
| I03 | `EMPRESAS` retorna só 2 filiais no token | Filtros incompletos | P1 | XS* |
| I04 | `analise_vendas_combustivel` timeout frequente | Vendas-combustivel inutilizável | P1 | S |
| I05 | Gateway 8050 chama EMPRESAS 2× no startup | Lentidão boot (~10s health) | P2 | S |
| I06 | Proxy httpx direto em presentation/app.py | Bypass circuit breaker | P2 | M |

*I01-I03 dependem de ação externa.

---

## 6. QA

| # | Problema | Impacto | Prioridade | Esforço |
|---|---|---|---|---|
| Q01 | Cobertura testes ~12% | Regressões não detectadas | P1 | L |
| Q02 | 3 suites falham (Settings × .env) | CI não confiável | P1 | M |
| Q03 | `webposto_endpoint_audit.py` classifica 422 como OBSOLETO | Auditoria enganosa | P1 | S |
| Q04 | `network_sales_audit.py` não testa WebPosto direto | Falso negativo combustíveis | P2 | M |
| Q05 | Sem teste E2E do fluxo snapshot-first | Regressão executive não detectada | P2 | M |
| Q06 | Sprint 21.3 aberta (endpoints quebrados) | Backlog QA não fechado | P2 | M |

---

## 7. Performance

| # | Problema | Impacto | Prioridade | Esforço |
|---|---|---|---|---|
| P01 | KPIs: 3 chamadas WebPosto síncronas por request | Latência 30-90s | P0 | M |
| P02 | `fetchDatasetAcrossCompanies` até 40 páginas × N empresas | UI trava em background | P1 | M |
| P03 | LMC_REDE payload grande em períodos longos | Timeout combustíveis | P1 | M |
| P04 | ProdutoCatalog busca PRODUTO sequencial por empresa | Latência catálogo | P2 | M |
| P05 | Executive polling 3s × 120s sem backoff | Requests desnecessários | P2 | S |
| P06 | Analytics cache TTL 60s — cold start lento | Primeiro request sempre lento | P3 | S |

---

## 8. Top 10 Dívidas Técnicas (Consolidado)

| Rank | ID | Problema | Prioridade |
|---|---|---|---|
| 1 | I01 | Token limita 2/11 filiais combustíveis | P0 |
| 2 | A01 | 8 entrypoints FastAPI | P0 |
| 3 | A02 | 7 clientes WebPosto | P0 |
| 4 | AN01 | Duas fontes de litros sem contrato | P0 |
| 5 | AN02 | 3 fluxos KPIs executivos | P0 |
| 6 | P01 | KPIs: 3 chamadas síncronas | P0 |
| 7 | AN03 | Reconciliação com timeout | P1 |
| 8 | F01 | Agregação multiselect no frontend | P1 |
| 9 | Q01 | Cobertura testes 12% | P1 |
| 10 | F04 | 14 dashboards legados | P1 |

---

*Sprint A02 — matriz de dívida técnica. Sem alteração de código.*
