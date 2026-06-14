# IA-4 — Snapshot Guard Audit Report

## Hipóteses avaliadas

### A) SnapshotGuard Onda 2 (`gateway/webposto_client.py`)

| Item | Resultado |
|------|-----------|
| Usado por rotas financeiras? | ❌ **Não** |
| Mensagem típica | `"Chamada WebPosto live bloqueada (allow_live=False)"` |
| Match com sintoma | ❌ Texto diferente |

### B) WebPostoClient produção (`src/gateway/webposto_client.py`)

| Item | Resultado |
|------|-----------|
| Usado por `fechamento_enterprise.py`? | ✅ **Sim** (`WebPostoClient()` linha 24) |
| Regra que bloqueou | `SimpleCircuitBreaker.is_blocked("despesas_financeiro_rede")` |
| Tipo | `CIRCUIT_OPEN` |
| Mensagem | **"Endpoint bloqueado temporariamente"** ✅ |

### C) Como o circuito abre

| Gatilho | Código | Duração |
|---------|--------|---------|
| 3 falhas consecutivas | `record_failure()` | 3600s (`circuit_block_seconds`) |
| HTTP 401 upstream | `block_endpoint()` imediato | 3600s |

Config: `src/core/config.py` → `circuit_fail_threshold=3`, `circuit_block_seconds=3600`.

### D) Estado atual (runtime)

- Permissão `despesas_financeiro_rede`: **true**
- Circuito: **aberto** (bloqueia antes de tentar live)
- Snapshot financeiro `/api/v1/financial/snapshot`: **vazio** (`fromSnapshot: false`, dados null)

## Regra que bloqueou

**Circuit Breaker in-memory** no `src/gateway/webposto_client.py`, **não** SnapshotGuard da Onda 2.

Provável sequência: falhas/401 anteriores em `CONSULTAR_DESPESAS_FINANCEIRO_REDE` → circuito latched por 1h → permissão redescoberta como true, mas breaker ainda ativo.

## Parecer IA-4

Bloqueio = **CIRCUIT_OPEN (resiliência backend)**, não SnapshotGuard, não Gateway Onda 2.
