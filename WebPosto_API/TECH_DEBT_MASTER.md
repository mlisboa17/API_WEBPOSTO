# TECH DEBT MASTER — LOGOS SPACE
## Sprint A02.5 | Agente 8 — Governança Técnica

| Campo | Valor |
|---|---|
| **Total itens** | 43 |
| **P0 (bloqueadores)** | 8 |
| **Data** | 2026-06-08 |
| **Base** | A01.1 + A02 + A02.5 |

---

## Resumo por Categoria

| Categoria | P0 | P1 | P2 | P3 | Total |
|---|---|---|---|---|---|
| Arquitetura | 2 | 2 | 3 | 1 | 8 |
| Backend | 1 | 4 | 3 | 2 | 10 |
| Frontend | 0 | 4 | 2 | 2 | 8 |
| Analytics | 3 | 2 | 1 | 1 | 7 |
| Fuel/WebPosto | 2 | 2 | 1 | 0 | 5 |
| QA | 0 | 3 | 2 | 0 | 5 |

---

## Registro Completo

### Arquitetura (8)

| ID | Problema | Impacto | Pri | Esf |
|---|---|---|---|---|
| A01 | 8 entrypoints FastAPI | Deploy errado, rotas órfãs | P0 | M |
| A02 | 7 clientes WebPosto | Comportamento inconsistente | P0 | L |
| A03 | Gateway 8050 duplica 8040 | 3 fluxos KPI, confusão | P1 | L |
| A04 | Subprojeto `logos-webposto-gateway/` | Deploy versão errada | P2 | M |
| A05 | `src/` não reflete domínios negócio | Onboarding lento | P2 | L |
| A06 | `routes_crud` + `auditoria` órfãos | Código morto aparente ativo | P2 | S |
| A07 | `main-mlisboa17.py` no repo | Deploy acidental | P3 | XS |
| A08 | Portas inconsistentes (8040/8041/8050) | Auditoria enganosa | P2 | S |

### Backend (10)

| ID | Problema | Impacto | Pri | Esf |
|---|---|---|---|---|
| B01 | Sync logs só memória | Perda telemetria restart | P1 | M |
| B02 | Refresh sem fila persistente | Race conditions | P1 | M |
| B03 | Paginação KPIs limit=500 | Subestimação dados | P1 | M |
| B04 | Normalização monetária divergente | Reconciliação falha | P1 | M |
| B05 | Auth mock JWT | Segurança inexistente | P2 | L |
| B06 | `/sync/*` retorna 500 | Sync inoperante | P2 | M |
| B07 | `/clientes/` retorna 500 | CRUD quebrado | P2 | M |
| B08 | Celery stubs | Background não funciona | P3 | L |
| B09 | `metrics/executive` Valkey hardcoded | Falha sem Valkey | P3 | S |
| B10 | Proxy httpx em presentation/app | Bypass circuit breaker | P2 | M |

### Frontend (8)

| ID | Problema | Impacto | Pri | Esf |
|---|---|---|---|---|
| F01 | Multiselect agrega no frontend | Lento + divergência | P1 | M |
| F02 | Timeout fuels 30s | Falha períodos longos | P1 | S |
| F03 | Executive fuels sem fallback direto | Card vazio | P1 | S |
| F04 | 14+ dashboards HTML legados | Fragmentação UX | P1 | M |
| F05 | `salesActiveSubview` fora URL | Estado perdido F5 | P2 | XS |
| F06 | `pageFuels` não consumido | Código morto | P3 | XS |
| F07 | `refreshSalesOnly` sem enrich catálogo | Nomes degradados | P2 | S |
| F08 | Gráficos CSS inline | Manutenção visual | P3 | M |

### Analytics (7)

| ID | Problema | Impacto | Pri | Esf |
|---|---|---|---|---|
| AN01 | Duas fontes litros sem contrato UX | Decisões erradas | P0 | S |
| AN02 | 3 fluxos KPIs executivos | Números divergentes | P0 | M |
| AN03 | Reconciliação timeout cadeia | Aceite não atingido | P1 | L |
| AN04 | `VENDA_ITEM_REDE` 401 | KPIs rede imprecisos | P0 | XS* |
| AN05 | Coverage sem cache próprio | Latência extra | P2 | S |
| AN06 | `FinancialSnapshotService` porta 8041 | Script quebrado | P3 | XS |
| AN07 | Cálculo DRE no frontend JS | Divergência classificação | P1 | M |

### Fuel / WebPosto (5)

| ID | Problema | Impacto | Pri | Esf |
|---|---|---|---|---|
| W01 | Token 2/11 filiais combustíveis | 18% cobertura | P0 | XS* |
| W02 | Endpoints `_REDE` 401 em massa | Loops por empresa | P0 | XS* |
| W03 | `analise_vendas_combustivel` timeout | Vendas-combustivel inútil | P1 | S |
| W04 | `vendas_combustivel_service` legado | Duplica fuel-summary | P2 | S |
| W05 | EMPRESAS 2× no boot 8050 | +10s startup | P2 | S |

### QA (5)

| ID | Problema | Impacto | Pri | Esf |
|---|---|---|---|---|
| Q01 | Cobertura testes ~12% | Regressões não detectadas | P1 | L |
| Q02 | 3 suites falham (Settings × .env) | CI não confiável | P1 | M |
| Q03 | Auditoria classifica 422 como OBSOLETO | Falsos positivos | P1 | S |
| Q04 | `network_sales_audit` não testa WebPosto | Auditoria inútil | P2 | M |
| Q05 | Sem E2E snapshot-first | Regressão performance | P2 | M |

*Depende de ação externa (Quality Automação).

---

## Top 10 Prioridades

1. W01/AN04 — Expansão token WebPosto (P0)
2. A01 — Unificar entrypoints (P0)
3. A02 — Consolidar clientes WebPosto (P0)
4. AN01 — Contrato LMC vs Vendidos na UI (P0)
5. AN02 — Unificar fluxos KPIs (P0)
6. F01 — Agregação multiselect no backend (P1)
7. Q01/Q02 — Corrigir CI e cobertura (P1)
8. B01 — Sync logs persistentes (P1)
9. F04 — Decommission dashboards legados (P1)
10. AN03 — Reconciliação performática (P1)

---

*Agente 8 — registro mestre. Sem alteração de código nesta sprint.*
