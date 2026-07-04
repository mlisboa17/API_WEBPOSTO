# PERFORMANCE-01 — Validação Final

**Status:** PASS (PCG 95/100)  
**Data:** 2026-07-04

## Evidência runtime

| Arquivo | Conteúdo |
|---|---|
| `docs/performance/PERFORMANCE_01_HTTP_RUNTIME_RAW.json` | Prompt 2 — fast path + background |
| `docs/performance/PERFORMANCE_01_CACHE_CONCURRENCY_RAW.json` | Prompt 3 — fuel cache + concurrency |
| `docs/performance/PERFORMANCE_01_SINGLE_FLIGHT_RAW.json` | Prompt 4 — single-flight race fix |

## Aceite por missão

| Missão | Resultado |
|---|---|
| Home imediata | PASS — 3.3 ms |
| Refresh background | PASS — 491 ms trigger |
| Fuel cache isolado | PASS — 0 warm requests |
| Concurrency medida | PASS — C3 = 51753 ms |
| Single-flight | PASS (após fix atômico por scope) |

## Single-flight — histórico honesto

- **Prompt 2:** PASS (2 POSTs, mesmo analysis_id)
- **Prompt 3 pós-alterações:** FAIL — 2 analysis_id em POST concurrente idle
- **Prompt 4 fix:** PASS — 2/5 POSTs + recheck durante RUNNING

## Testes unitários

```
tests/unit/test_owner_analysis_single_flight.py — 2/2 PASS
tests/unit/test_owner_analysis_progress_callback.py — PASS
tests/unit/test_owner_analysis_utc_time.py — PASS
```

## Scripts

```bash
python scripts/performance_01_http_runtime_validation.py
python scripts/performance_01_cache_concurrency.py
python scripts/performance_01_single_flight_validation.py
```

## Pergunta de aceite

> Home imediata + refresh background + cache isolado + single-flight sem duplicação?

**SIM** — com métricas em `PERFORMANCE_01_RUNTIME_REPORT.md`.
