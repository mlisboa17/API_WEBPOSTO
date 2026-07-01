# RT02_RUNTIME_VALIDATION_REPORT — IA-6

**Data:** 2026-06-14 | **Script:** `scripts/audit_rt02_performance.py`

## Testes primários

| Endpoint | Status | Tempo | Origem | Modo resiliência |
|---|---|---|---|---|
| `/health` | 200 | 0,02s | — | — |
| `/v1/financial/overview` | 200 | 0,02s | snapshot | `snapshot_first` |
| `/v1/financial/expenses` | 200 | 0,01s | snapshot | `snapshot_first` |
| `/v1/stock` | 200 | 0,02s | snapshot | `snapshot_first` |
| `/v1/sales` | 200 | 8,02s | snapshot | `snapshot_fallback` |

**Primary OK:** 5/5

## API responsiva

- Health permanece **200**
- Nenhum timeout > 22s
- Cockpits F08 respondem durante probes de regressão

## Frontend

Shell `/app/financial` não revalidado em browser nesta execução; APIs alimentam telas Receitas, Despesas e Tanques com latência compatível com UX fluida.
