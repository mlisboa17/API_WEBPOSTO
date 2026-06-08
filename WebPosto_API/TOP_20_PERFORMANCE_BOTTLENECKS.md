# TOP 20 PERFORMANCE BOTTLENECKS — LOGOS SPACE
## Sprint A02.5 | Agente 6 — Performance

| Campo | Valor |
|---|---|
| **Data** | 2026-06-08 |
| **Classificação** | P0 = bloqueador, P1 = alto, P2 = médio |

---

| # | Gargalo | Classificação | Impacto | Domínio |
|---|---|---|---|---|
| 1 | `fetchByCompaniesSequential` — N requests seriais para multiselect KPIs/DRE | **P0** | UI trava 30-90s × N empresas | Frontend |
| 2 | Token WebPosto limita 2/11 filiais — loops inúteis por empresa | **P0** | 82% rede sem dados | Integração |
| 3 | `VENDA_ITEM_REDE` e `LMC_REDE` retornam 401 para maioria das filiais | **P0** | KPIs rede com buracos | Integração |
| 4 | KPIs backend: 3 chamadas WebPosto síncronas (expenses + sales + stock) | **P0** | Latência 30-90s por request | Backend |
| 5 | Agregação multiselect no frontend (`aggregateKpiResults`, `rebuildFuelExecutivePayload`) | **P1** | CPU browser alta; divergência | Frontend |
| 6 | `fetchFuelExecutive` timeout 30s (vs 90s analytics) | **P1** | Timeout em períodos >15 dias | Frontend |
| 7 | `fetchDatasetAcrossCompanies` — 40 páginas × N empresas sequencial | **P1** | Background trava UI | Frontend |
| 8 | `ExecutiveSnapshotService.collect` — filiais sequenciais no backend | **P1** | Refresh lento multiselect | Backend |
| 9 | Ausência cache dedicado para `lmc_rede` (só analytics_cache 60s) | **P1** | Hit WebPosto a cada refresh | Backend |
| 10 | Card fuels executive sem fallback se snapshot.fuel null | **P1** | Card vazio apesar de cache 60s | Frontend |
| 11 | Paginação KPIs `limit=500` sem garantia de completude | **P1** | Subestimação faturamento | Backend |
| 12 | `analise_vendas_combustivel` timeout em períodos longos | **P1** | Endpoint inutilizável | Integração |
| 13 | Executive polling 3s × 120s sem backoff exponencial | **P2** | Requests desnecessários | Frontend |
| 14 | Gateway 8050 chama `EMPRESAS` 2× no startup | **P2** | Boot ~10s health | Infra |
| 15 | `discover_permissions` testa 26+ endpoints no boot/TTL expiry | **P2** | Pico latência startup | Backend |
| 16 | Sync logs em memória — re-fetch após restart | **P2** | Telemetria perdida | Backend |
| 17 | Snapshot JSON disco I/O sem compressão | **P2** | I/O lento em storage fraco | Infra |
| 18 | Refresh snapshot `asyncio.create_task` sem fila persistente | **P2** | Perda refresh no restart | Backend |
| 19 | `metrics/executive` conecta Valkey host hardcoded | **P2** | Falha se Valkey down | Backend |
| 20 | Sem testes E2E de performance snapshot-first | **P2** | Regressões não detectadas | QA |

---

## Quick Wins (A03)

| # | Ação | Ganho estimado |
|---|---|---|
| 5 | Mover agregação multiselect → backend | -40% CPU frontend |
| 6 | Alinhar timeout fuels 30s → 90s | -60% timeouts fuels |
| 13 | Backoff exponencial no polling (3s→5s→10s→30s) | -50% requests polling |
| 14 | Unificar EMPRESAS no startup gateway | -5s boot |
| 9 | Cache LMC dedicado TTL 5-15min | -70% hits WebPosto fuels |

---

*Agente 6 — sem alteração de código nesta sprint.*
