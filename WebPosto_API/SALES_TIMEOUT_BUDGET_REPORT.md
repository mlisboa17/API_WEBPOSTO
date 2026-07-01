# SALES_TIMEOUT_BUDGET_REPORT — HOTFIX P0

## Configuração

| Setting | Valor | Env |
|---|---|---|
| `sales_live_timeout_seconds` | **8** | `SALES_LIVE_TIMEOUT_SECONDS` |
| `sales_total_budget_seconds` | **22** | `SALES_TOTAL_BUDGET_SECONDS` |
| `circuit_breaker_timeout` | 60 | existente |

## Implementação

```python
# sales_resilience_service._attempt_live
task = asyncio.create_task(overview.get_sales(...))
await asyncio.wait_for(task, timeout=sales_live_timeout_seconds)
# em TimeoutError: task.cancel() + snapshot fallback
```

## Regras

| Cenário | Comportamento |
|---|---|
| Live < 8s | Retorna live + grava snapshot |
| Live > 8s | Cancela task, abre circuito sales, snapshot |
| Circuit OPEN | Pula live, snapshot direto |
| Sem snapshot | `success: false`, `degraded: true` |

## Event loop

Cliente permanece async; cancelamento via `asyncio.wait_for` + `task.cancel()` — sem threadpool necessário (httpx já async).
