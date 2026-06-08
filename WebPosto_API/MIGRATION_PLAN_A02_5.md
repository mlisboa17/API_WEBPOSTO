# LOGOS SPACE — Migration Plan A02.5
## Consolidação Física da Arquitetura — Plano de Execução

| Campo | Valor |
|---|---|
| **Sprint** | A02.5 (planejamento) → A03..A05 (execução) |
| **Pré-requisitos** | 10 documentos A02.5 |
| **Princípio** | Strangler fig — migrar sem quebrar produção |
| **Data** | 2026-06-08 |

---

## Visão Geral

```
A02.5 (docs)  →  FASE 1 Entrypoints  →  FASE 2 WebPosto  →  FASE 3 Analytics
                      ↓                      ↓                    ↓
                 FASE 4 Dashboards  →  FASE 5 Snapshot First  →  A04 DW
```

| Fase | Sprint execução | Duração | Risco | Entregável |
|---|---|---|---|---|
| 1 — Entrypoints | A03 S1 | 2 sem | Baixo | 1 launcher oficial |
| 2 — WebPosto | A03 S2-S3 | 3 sem | Médio | 1 client físico |
| 3 — Analytics | A03 S3-S4 | 2 sem | Médio | 1 fluxo KPI |
| 4 — Dashboards | A04 S1-S2 | 3 sem | Baixo | 1 SPA oficial |
| 5 — Snapshot First | A03-A04 | 4 sem | Médio | 7 views snapshot |

---

## FASE 1 — Entrypoints (Agente 1)

**Objetivo:** `src/main.py:8040` como único entrypoint de produção.

| # | Ação | Tipo | Esforço | Sprint |
|---|---|---|---|---|
| 1.1 | Banner "GATEWAY AUXILIAR" no startup 8050 | Código | XS | A03 |
| 1.2 | Arquivar `main-mlisboa17.py`, `main_minimal.py` → `_archive/` | Código | XS | A03 |
| 1.3 | Remover `explorador_standalone.py` do repo ativo | Código | XS | A03 |
| 1.4 | CI: testes exclusivamente via `create_app()` | CI | M | A03 |
| 1.5 | Runbooks: porta 8040 oficial, 8050 auxiliar | Doc | XS | A02.5 ✅ |
| 1.6 | Deprecar subprojeto `logos-webposto-gateway/` | Processo | S | A04 |

**Critério de aceite:**
- [ ] Nenhum deploy script referencia entrypoints legados
- [ ] CI verde com `create_app()`
- [ ] Health 8040 < 3s

**Rollback:** Entrypoints legados permanecem em `_archive/`.

---

## FASE 2 — WebPosto Client (Agente 2)

**Objetivo:** `src/integrations/webposto/client.py` como único client HTTP.

| # | Ação | Tipo | Esforço | Sprint |
|---|---|---|---|---|
| 2.1 | Criar `src/integrations/webposto/` — move de gateway | Código | M | A03 |
| 2.2 | Migrar `fetch_multi_posto()` do GatewayWebPostoClient | Código | M | A03 |
| 2.3 | Substituir imports obsoletos (`src/webposto/`, `infrastructure/`) | Código | M | A03 |
| 2.4 | Lint: proibir imports de clients legados | CI | S | A03 |
| 2.5 | Congelar proxy httpx em 8050 — bugfix only | Processo | — | A03 |
| 2.6 | Solicitar expansão token Quality (2→11 filiais) | Negócio | — | Paralelo |

**Critério de aceite:**
- [ ] Zero imports de `src/webposto/client.py` em código ativo
- [ ] `GatewayWebPostoClient` delegando ao oficial
- [ ] Testes de integração passam com client único

---

## FASE 3 — Analytics (Agente 3)

**Objetivo:** `AnalyticsService` como único engine KPI/DRE; eliminar fluxos paralelos.

| # | Ação | Tipo | Esforço | Sprint |
|---|---|---|---|---|
| 3.1 | Redirect Adelaide KPIs (8050) → `/api/v1/kpis` (8040) | Código | S | A03 |
| 3.2 | Deprecar `fetch_executive_kpis` e `get_executive_metrics` | Código | M | A03 |
| 3.3 | Mover agregação multiselect → backend endpoint | Código | L | A03 |
| 3.4 | Aumentar limit paginação KPIs ou garantir completude | Código | M | A03 |
| 3.5 | Contrato UX: labels "Litros LMC" vs "Litros Vendidos" | Frontend | S | A03 |
| 3.6 | Unificar normalização monetária analytics/network | Código | M | A04 |

**Critério de aceite:**
- [ ] Executive view usa apenas `/api/v1/kpis` + snapshot
- [ ] Multiselect: 1 request backend (não N sequenciais)
- [ ] KPIs rede e individual reconciliam ±1%

---

## FASE 4 — Dashboards (Agente 5)

**Objetivo:** `frontend/index.html` como única superfície de produção.

| # | Ação | Tipo | Esforço | Sprint |
|---|---|---|---|---|
| 4.1 | Remover HTML obsoletos da raiz (D-008..D-014) | Código | S | A04 |
| 4.2 | Redirect `/dashboard` (8050) → `/app/financial` | Código | S | A04 |
| 4.3 | Migrar funcionalidades úteis Adelaide → SPA views | Código | L | A04 |
| 4.4 | Arquivar `static/`, `theme/` → `_archive/` | Código | M | A05 |
| 4.5 | Remover rotas UI de `presentation/app.py` | Código | M | A05 |
| 4.6 | Remover `src/frontend/dashboard.jsx` | Código | XS | A04 |

**Critério de aceite:**
- [ ] Zero dashboards HTML ativos fora de `frontend/`
- [ ] Adelaide redirect funcional
- [ ] Todas views acessíveis via SPA

---

## FASE 5 — Snapshot First (Agente 7)

**Objetivo:** Todas views analíticas seguem Dashboard → Snapshot → Cache → WebPosto.

| # | Ação | Tipo | Esforço | Sprint |
|---|---|---|---|---|
| 5.1 | Executive snapshot — manter e melhorar (já pronto) | — | — | ✅ |
| 5.2 | `FuelSnapshotService` para view `fuels` | Código | L | A03 |
| 5.3 | Prewarm snapshot no startup (período default) | Código | M | A03 |
| 5.4 | Backoff exponencial no polling executive | Código | S | A03 |
| 5.5 | Cache LMC dedicado TTL 5-15min | Código | M | A03 |
| 5.6 | Unificar `FinancialSnapshotService` → Executive | Código | M | A04 |
| 5.7 | Fila persistente refresh (SQLite/Redis lock) | Código | L | A04 |
| 5.8 | Persistir sync logs (SQLite) | Código | M | A04 |
| 5.9 | Alinhar timeout fuels 30s → 90s | Código | XS | A03 |
| 5.10 | E2E test snapshot-first (< 8s render) | QA | M | A04 |

**Critério de aceite:**
- [ ] Render inicial ≤ 8s em todas views analíticas
- [ ] Zero chamada WebPosto síncrona no render
- [ ] `lastUpdated` visível em todas views
- [ ] Refresh background não bloqueia UI

---

## FASE 6 — Performance Quick Wins (Agente 6)

| # | Ação | Ganho | Sprint |
|---|---|---|---|
| P1 | Agregação multiselect backend | -40% CPU frontend | A03 |
| P2 | Timeout fuels 30s → 90s | -60% timeouts | A03 |
| P3 | Backoff polling | -50% requests | A03 |
| P4 | Cache LMC dedicado | -70% hits WebPosto | A03 |
| P5 | EMPRESAS 1× no boot 8050 | -5s startup | A04 |

---

## FASE 7 — Tech Debt (Agente 8)

| Prioridade | Itens | Sprint alvo |
|---|---|---|
| P0 (8) | Token, entrypoints, clients, litros UX, KPIs paralelos | A03 + negócio |
| P1 (16) | Agregação, CI, sync logs, dashboards legados | A03-A04 |
| P2 (13) | Auth mock, CRUD 500, coverage cache | A04-A05 |
| P3 (6) | Celery stubs, Valkey hardcoded, código morto | A05+ |

---

## Cronograma Consolidado

| Semana | Sprint | Foco |
|---|---|---|
| S1 A03 | Entrypoints + Fuel Snapshot + timeout fuels | Fases 1, 5.2, 5.9 |
| S2 A03 | WebPosto client move + multiselect backend | Fases 2, 3.3 |
| S3 A03 | Analytics unificação + cache LMC + polling | Fases 3, 5.4, 5.5 |
| S4 A03 | Prewarm startup + redirect Adelaide KPIs | Fases 3.1, 5.3 |
| S1 A04 | Dashboards remoção + redirect Adelaide | Fase 4 |
| S2 A04 | Financial snapshot unificação + fila refresh | Fases 5.6, 5.7 |
| S3 A04 | Sync logs + E2E performance | Fases 5.8, 5.10 |
| S4 A05 | Arquivar static/theme + remover gateway UI | Fases 4.4, 4.5 |

---

## Dependências Externas

| Dependência | Responsável | Impacto |
|---|---|---|
| Expansão token WebPosto 2→11 filiais | Quality Automação | P0 — 82% rede sem dados |
| Endpoints `_REDE` habilitados | Quality Automação | P0 — loops por empresa |
| Valkey/Redis em produção | Infra | P2 — cache distribuído |

---

## Métricas de Sucesso

| Métrica | Atual | Alvo A05 |
|---|---|---|
| Entrypoints ativos | 8 | 1 (+ launcher) |
| Clientes WebPosto | 7 | 1 |
| Dashboards ativos | 21 | 1 |
| Views snapshot-first | 1/7 | 7/7 |
| Risco arquitetural | 58 | ≤35 |
| Maturidade | 6.0 | ≥7.5 |
| Cobertura testes | 12% | ≥40% |

---

*Plano A02.5 — execução física inicia na Sprint A03. Nenhum código alterado nesta sprint.*
