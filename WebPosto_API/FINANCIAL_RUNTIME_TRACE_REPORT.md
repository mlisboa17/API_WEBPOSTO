# IA-7 — Financial Runtime Trace Report

**Ambiente:** `http://127.0.0.1:8050`  
**Período teste:** `dataInicial=2026-06-01`, `dataFinal=2026-06-07`

## Trace 1 — Financeiro → Receitas

| Etapa | Resultado |
|-------|-----------|
| Request | `GET /v1/financial/overview?dataInicial=2026-06-01&dataFinal=2026-06-07` |
| HTTP status | **200** |
| `success` | **false** |
| `error.status` | **503** |
| `error.type` | **CIRCUIT_OPEN** |
| `error.message` | **Endpoint bloqueado temporariamente** |
| `error.endpoint` | `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` |

## Trace 2 — Financeiro → Despesas

| Etapa | Resultado |
|-------|-----------|
| Request | `GET /v1/financial/expenses?dataInicial=2026-06-01&dataFinal=2026-06-07&page=1&limit=10` |
| HTTP status | **200** |
| `success` | **false** |
| `error.status` | **503** |
| `error.type` | **CIRCUIT_OPEN** |
| `error.message` | **Endpoint bloqueado temporariamente** |
| `error.endpoint` | `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` |

## Trace auxiliar — Permissões

| Request | Resultado |
|---------|-----------|
| `GET /v1/permissions` | `despesas_financeiro_rede: true` |

## Trace auxiliar — Snapshot financeiro

| Request | Resultado |
|---------|-----------|
| `GET /api/v1/financial/snapshot?...` | `fromSnapshot: false`, dados null |

## Classificação HTTP

| Código | Presente? |
|--------|-----------|
| 401 | ❌ (não no response atual; possível causa histórica do circuito) |
| 403 | ❌ |
| 404 | ❌ |
| 429 | ❌ |
| 500 | ❌ |
| 503 | ✅ (lógico, dentro de `error.status`) |

## Frontend

`apiClient.js` interpreta `success: false` → `throw new Error("Endpoint bloqueado temporariamente")` → banner `#error`.

## Parecer IA-7

Falha reproduzida em runtime. Causa imediata: **circuit breaker aberto** no endpoint de despesas rede.
