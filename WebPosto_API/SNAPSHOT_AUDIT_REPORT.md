# SNAPSHOT AUDIT REPORT — Sprint A03.6
## LOGOS SPACE Combustíveis

| Campo | Valor |
|---|---|
| **Data** | 2026-06-08 |
| **Escopo** | Executive / Fuel / Financial snapshots |

---

## Resumo

| Serviço | TTL | Resultado |
|---|---|---|
| ExecutiveSnapshotService | 5 min | **PASSOU** (com ressalva stale UI) |
| FuelSnapshotService | 15 min | **PASSOU** |
| FinancialOperationalSnapshotService | 5 min | **PASSOU** |
| SnapshotStore (infra) | — | **PASSOU** (correção A03.6) |

---

## ExecutiveSnapshotService

| Critério | Resultado | Evidência |
|---|---|---|
| TTL funcionando | **PASSOU** | `SnapshotStore` 300s; miss após expiração |
| Cache reutilizado | **PASSOU** | `fromSnapshot: true`, ~2s vs refresh background |
| Refresh background | **PASSOU** | `POST /executive/refresh` → `status: started` |
| Invalidação | **PASSOU** | Expirado retorna `fromSnapshot: false` |
| Chaves corretas | **PASSOU** | `{dataIni}:{dataFim}:{empresaCodigo}` |
| Duplicação | **PASSOU** | 1 arquivo por chave em `snapshots/executive/` |
| Vazamento memória | **RISCO→CORRIGIDO** | Expirados não permanecem em `_memory` (fix A03.6) |

**Arquivos disco:** `2026-06-03_2026-06-08_11495.json`, `2026-06-03_2026-06-08_.json`

**Ressalva:** `lastUpdated` antigo (>30min) exibe aviso stale no frontend — comportamento esperado.

---

## FuelSnapshotService

| Critério | Resultado | Evidência |
|---|---|---|
| TTL 15 min | **PASSOU** | `FUEL_SNAPSHOT_TTL_SECONDS = 900` |
| Cache miss rápido | **PASSOU** | GET snapshot ~22ms sem hit |
| Refresh | **PASSOU** | POST refresh ~2s trigger |
| Chaves | **PASSOU** | `snapshots/fuel/2026-06-03_2026-06-08_11495.json` |
| Duplicação | **PASSOU** | Sem arquivos duplicados por chave |
| Frontend snapshot-first | **PASSOU** | `loadFuelWithSnapshotFirst()` em `app.js` |

**RISCO:** Após miss, fallback live `/fuel/executive` ~17s — timeout UX em períodos longos.

---

## FinancialOperationalSnapshotService

| Critério | Resultado | Evidência |
|---|---|---|
| TTL 5 min | **PASSOU** | `FINANCIAL_SNAPSHOT_TTL_SECONDS = 300` |
| API snapshot/refresh | **PASSOU** | 200 OK |
| Conteúdo | **PASSOU** | overview + expenses + accounts coletados |
| Integração UI | **RISCO** | Views expenses/accounts ainda usam live API |
| Chaves | **PASSOU** | `snapshots/financial/2026-06-03_2026-06-08_11495.json` |

---

## Correção A03.6

**Arquivo:** `src/services/snapshot_store.py`

Snapshots expirados lidos do disco não são mais mantidos em memória — elimina acúmulo silencioso.

---

## Classificação Final

| Item | Status |
|---|---|
| TTL | **PASSOU** |
| Refresh | **PASSOU** |
| Chaves | **PASSOU** |
| Memória | **PASSOU** (pós-fix) |
| UI financial snapshot | **RISCO** |
| Fuel live fallback | **RISCO** |

---

*Sprint A03.6 — auditoria snapshots concluída.*
