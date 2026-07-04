# PERFORMANCE-01 — Auditoria de Cache/Snapshot Existente

Data: 2026-07-03

## Respostas objetivas

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Snapshot de vendas? | **Parcial** — `FuelSnapshotService` (`snapshots/fuel`, TTL 15min) |
| 2 | Snapshot de combustível? | **Sim** — `FuelSnapshotService` + `FuelAnalyticsService` |
| 3 | Cache do fuel-summary? | **Sim no serviço de snapshot** — **NÃO usado pelo Discovery Engine** |
| 4 | Cache por tenant? | **Sim** — chave `build_snapshot_key(data_inicial, data_final, empresa_codigo)` |
| 5 | Cache por empresaCodigo? | **Sim** — via suffix em snapshot keys |
| 6 | Cache por período? | **Sim** — datas na chave |
| 7 | TTL? | **Sim** — `FuelSnapshotService`: 900s; `ActionCenterSnapshotService`: 300s; `SnapshotStore` genérico |
| 8 | stale-while-revalidate? | **Sim** — `ActionCenterSnapshotService.get_or_collect` retorna stale + flag |
| 9 | Invalidation? | **TTL expiry** — sem invalidação event-driven |
| 10 | Discovery Engine ignora cache? | **Sim** — `FuelRevenueDetector` chama `AnalyticsService.get_fuel_summary` direto |
| 11 | FuelRevenueDetector requests duplicadas? | **Sim** — 2× `get_fuel_summary`/tenant (atual + baseline), cada uma refaz cadeia WebPosto |
| 12 | Owner Action Center dispara nova análise a cada GET? | **Sim** — `/top5` executa pipeline completo síncrono |
| 13 | React Query repete? | `staleTime: 0` — refetch agressivo no frontend |
| 14 | Fast Refresh? | Pode remontar componente em dev — não medido como produção |
| 15 | Home >1 request? | **Sim** — `getTop5Decisions` + `getBusinessHealth` (2 requests backend) |

---

## Infraestrutura reutilizável (NÃO criar segundo sistema)

### `SnapshotStore` (`src/services/snapshot_store.py`)

- Memória + disco JSON
- TTL configurável
- `load`, `load_stale`, `save`
- **Reutilizar para:** Tenant Registry, Analysis Snapshot, fuel cache do detector

### `FuelSnapshotService` (`src/services/fuel_snapshot_service.py`)

- TTL: **900s (15 min)**
- Chave: `build_snapshot_key(data_inicial, data_final, empresa_codigo)`
- `get_snapshot`, `collect`, `refresh`, `start_refresh_background`
- Single-flight por key (`_running` set)

### `ActionCenterSnapshotService`

- TTL: **300s**
- stale-while-revalidate pattern
- **Usado em** `/business-health` — **não** em `/top5` discovery

### `permission_cache.py`

- Cache **global** in-process
- TTL: `CoreConfig.permission_ttl_seconds` (3600s default)
- **Problema:** não isola por credencial

### Outros snapshots (não usados pela Home)

- `FinancialSnapshotService`, `ExecutiveSnapshotService`, `CashOperationsSnapshotService`, etc.
- Padrão comum: `SnapshotStore` + TTL + `get_or_collect`

---

## Lacunas confirmadas

1. **Nenhum Analysis Snapshot** para resultado do Discovery Engine (`monitoring_state`, `analysis_proof`, decisions)
2. **Nenhum Tenant Registry cache** — `TenantDiscoveryService` chama EMPRESAS a cada request
3. **FuelRevenueDetector bypassa FuelSnapshotService**
4. **Nenhum background job** para refresh da análise diária
5. **Nenhum single-flight** no Owner Action Center `/top5`

---

## Decisão PERFORMANCE-01

| componente | ação |
|---|---|
| Fuel data | **Reutilizar** `SnapshotStore` pattern (mesmo de `FuelSnapshotService`) |
| Tenant registry | **Novo registry** sobre `SnapshotStore`, TTL longo (~1h) |
| Analysis result | **Novo** `OwnerAnalysisSnapshotService` sobre `SnapshotStore` |
| Permission | **Estender** cache existente com key por `credential_fingerprint` |
| Background | **asyncio.create_task** (padrão já usado em `FuelSnapshotService.start_refresh_background`) |

Não adicionar Redis/Celery nesta sprint — solução mínima compatível com arquitetura atual.
