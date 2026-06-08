# SNAPSHOT FIRST ARCHITECTURE — LOGOS SPACE
## Sprint A02.5 | Agente 7 — Arquitetura de Dados

| Campo | Valor |
|---|---|
| **Princípio** | Dashboard → Snapshot → Cache → WebPosto (background only) |
| **Data** | 2026-06-08 |

---

## Camadas Mapeadas (Estado Atual)

| Camada | Serviço | Localização / TTL | Status |
|---|---|---|---|
| Executive Snapshot | `ExecutiveSnapshotService` | `snapshots/executive/*.json` + memória | PRONTO |
| Financial Snapshot | `FinancialSnapshotService` | HTTP 8041 / scripts | LEGADO |
| Analytics Cache | `analytics_cache.py` | In-memory 60s | PRONTO |
| Produto Catalog | `ProdutoCatalogService` | In-memory 24h | PRONTO |
| Frontend Cache | `app.js` `state.cache` | Browser Map | PRONTO |
| Audit Snapshot | `auditSnapshot.js` | `/snapshots/*.json` estático | EXPERIMENTAL |
| Comparativo | `snapshotService.js` | API live | EXPERIMENTAL |
| Valkey/Redis | `valkey_manager.py` | 60-300s | PARCIAL (só 8050) |
| Sync Logs | `IntegrationLogService` | Memória 1000 entradas | PARCIAL |

---

## Estado por View

| View | Atual | Alvo A03 |
|---|---|---|
| `executive` | Snapshot-first ✅ (8s timeout + refresh background) | Manter + melhorar |
| `fuels` | Chamada direta 30s ❌ | Snapshot-first |
| `sales` fuels | Chamada direta 30s ❌ | Cache 60s + snapshot |
| `dashboard` | Chamada direta overview ❌ | Snapshot parcial |
| `expenses/accounts/stock` | Paginação direta ❌ | Cache + background |

---

## Arquitetura Alvo

```
┌─────────────┐
│  Dashboard  │  ← render imediato (< 3s)
└──────┬──────┘
       │ GET /snapshot (≤8s)
┌──────▼──────┐
│  Snapshot   │  ← disco JSON + memória (persistente)
│  (disco)    │
└──────┬──────┘
       │ miss / stale
┌──────▼──────┐
│   Cache     │  ← Valkey/Redis + analytics_cache 60s
│  (quente)   │
└──────┬──────┘
       │ miss / TTL expired
┌──────▼──────┐
│  Background │  ← worker/fila (nunca bloqueia UI)
│   Worker    │
└──────┬──────┘
       │
┌──────▼──────┐
│  WebPosto   │  ← único ponto de I/O externo
│   Client    │
└─────────────┘
```

---

## Fases de Migração

| Fase | Sprint | Ação |
|---|---|---|
| 1 | A02.5 ✅ | Executive snapshot implementado |
| 2 | A03 | `FuelSnapshotService` para view `fuels` |
| 3 | A03 | Prewarm snapshot no startup (período default) |
| 4 | A03 | Migrar `analytics_cache` → Valkey (opcional) |
| 5 | A04 | Unificar `FinancialSnapshotService` → `ExecutiveSnapshotService` |
| 6 | A04 | Fila persistente para refresh (SQLite/Redis lock) |
| 7 | A04 | Persistir sync logs |
| 8 | A05 | Frontend `localStorage` cache para offline instant |

---

## Chaves de Snapshot

```
{dataInicial}:{dataFinal}:{empresaCodigo}
→ snapshots/executive/{key}.json
```

Futuro: `snapshots/fuel/{key}.json`, `snapshots/financial/{key}.json`

---

## Regras Oficiais

1. Nenhuma view analítica faz chamada WebPosto síncrona no render inicial
2. Timeout snapshot ≤ 8s; timeout refresh trigger ≤ 5s
3. Polling com backoff exponencial (3s → 5s → 10s → 30s)
4. `lastUpdated` obrigatório em toda view analítica
5. Erro WebPosto → manter último snapshot; nunca timeout bruto na UI

---

*Agente 7 — sem alteração de código nesta sprint.*
