# PERFORMANCE-01 — Runtime Report Final

**Sprint:** Fast Daily Analysis Loop  
**Data:** 2026-07-04  
**Evidência:** `docs/performance/PERFORMANCE_01_HTTP_RUNTIME_RAW.json`, `PERFORMANCE_01_CACHE_CONCURRENCY_RAW.json`, `PERFORMANCE_01_SINGLE_FLIGHT_RAW.json`

## Baseline histórico (honesto)

| Fase | FULL_ANALYSIS | Notas |
|---|---|---|
| Original bloqueante | ~205.5 s | Home aguardava discovery |
| Instrumentado Prompt 2 | ~86–94 s | Background + 3 tenants |
| Cold pós-cache/concurrency | **47.3 s** | `OWNER_ANALYSIS_MAX_CONCURRENCY=3` |
| Warm pós-cache | **7 ms** | 0 requests WebPosto |

## Fast path (HTTP final)

| Métrica | Valor | Critério |
|---|---|---|
| HOME_RESPONSE_MS | 3.3 ms | < 1000 ms |
| REFRESH_TRIGGER_MS | 491 ms | < 1000 ms |
| POST_REFRESH_HOME_MS | 23.2 ms | < 1000 ms |
| freshness | FRESH / STALE_REFRESHING | snapshot válido |
| tenant_count | 3 | 5555, 11495, 74014 |
| analysis_proof | preservado | PASS |

## Fuel cache

| Métrica | Cold | Warm |
|---|---|---|
| total_ms | 47321.2 | 7.0 |
| cache_hits | 0 | 3 |
| cache_misses | 3 | 0 |
| WebPosto requests | 84 | 0 |
| VENDA_ITEM requests | 60 | 0 |
| speedup | — | 6760× |

**Bug corrigido:** `_fetch_fuel_data_live` retornava `None` após HTTP com linhas vazias → cache nunca gravava.  
**Cache key:** `discovery_fuel:{tenant_id}:{empresa_codigo}:{period_start}:{period_end}`  
**Isolamento:** PASS (5555 / 11495 / 74014)

## Concurrency

| C | total_ms | speedup vs C1 | 429 | timeout | 5xx | failures |
|---|---|---|---|---|---|---|
| 1 | 53347 | 1.0 | 0 | 0 | 0 | 0 |
| 2 | 70056 | 0.76 | 0 | 0 | 0 | 0 |
| 3 | 51753 | 1.03 | 0 | 0 | 0 | 0 |

**Escolhida:** `OWNER_ANALYSIS_MAX_CONCURRENCY=3` — mais rápido que C1 sem erros; C2 pior (contention WebPosto).

## Single-flight

| Teste | Resultado |
|---|---|
| 2 POSTs mesmo scope (job RUNNING) | PASS — 1 analysis_id |
| 5 POSTs mesmo scope | PASS — 0 jobs novos |
| Scopes diferentes | PASS — IDs distintos |
| Recheck durante RUNNING | PASS |

**Race anterior:** check/registro não serializados por scope; `_running_job_for_scope` fazia pop com efeito colateral; job ultra-rápido liberava scope antes do 2º POST.  
**Correção:** `asyncio.Lock` por scope + reserva atômica + status RUNNING síncrono antes do `create_task`.

## PCG Final

| Gate | Status |
|---|---|
| Single-flight | PASS |
| Cache multi-tenant | PASS |
| Refresh sem duplicar job overlap | PASS |
| analysis_proof | PASS |
| Home não bloqueia | PASS |
| Mock | NÃO usado |
| Thresholds | NÃO alterados |

**Score: 95/100** — limitação: single-flight in-memory (1 worker uvicorn); multi-worker exigiria lock distribuído.

## Limitações restantes

- Cache current+baseline no mesmo snapshot por período
- `FuelSnapshotService` (LMC) não usado pelo detector
- C2 mais lento que C1 em runtime medido
- Análise warm ~7 ms assume fuel cache quente + permission/registry warm
