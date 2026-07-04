# Fast Daily Analysis Loop — PERFORMANCE-01

## Decisão

Reutilizar `SnapshotStore` existente. **Não** criar segundo store genérico.

## Componentes

| Componente | Papel |
|---|---|
| `OwnerAnalysisSnapshotService` | Último resultado válido + refresh lifecycle |
| `owner_analysis_runner.py` | Execução Discovery multi-tenant |
| `owner_analysis_models.py` | Freshness + Refresh enums |
| `SnapshotStore` | Memória + disco JSON (`snapshots/owner_analysis/`) |

## Freshness

- `FRESH` — dentro de 30 min
- `STALE_REFRESHING` — snapshot visível + refresh RUNNING
- `STALE` — expirado, sem refresh
- `NO_ANALYSIS` — sem snapshot válido

## HTTP

| Método | Path | Função |
|---|---|---|
| GET | `/api/v1/owner-action-center/top5` | Snapshot atual + freshness (<1s) |
| POST | `/api/v1/owner-action-center/analysis/refresh` | Dispara refresh background |
| GET | `/api/v1/owner-action-center/analysis/status/{id}` | Progresso real |
| GET | `/api/v1/owner-action-center/analysis/metrics` | Métricas runtime |

## Single-flight key

`{period_start}:{period_end}:all_discovered:FuelRevenueDetector:{empresa|all}`

**Atomicidade (PERFORMANCE-01 fix):** `asyncio.Lock` por scope + reserva atômica em `_acquire_refresh_scope`. Duas requisições simultâneas no mesmo scope retornam o mesmo `analysis_id`; a segunda recebe `already_running=true`.

## Background

`asyncio.create_task` (padrão `FuelSnapshotService`).

## Fuel cache (Discovery)

`SnapshotStore` em `snapshots/discovery_fuel/` — path VENDA_ITEM do detector.

- TTL período atual (inclui hoje): **5 min**
- TTL período fechado: **24 h**
