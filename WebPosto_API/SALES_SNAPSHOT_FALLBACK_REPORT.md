# SALES_SNAPSHOT_FALLBACK_REPORT — HOTFIX P0

## Kind snapshot

`financial_sales` em `snapshots/financial/financial_sales_{period}_{empresa}.json`

## Matriz de resposta

| Condição | HTTP | success | source | mode |
|---|---|---|---|---|
| Live OK | 200 | true | live | live |
| Timeout/erro + snapshot | 200 | true | snapshot | snapshot_fallback |
| Circuit OPEN + snapshot | 200 | true | snapshot | snapshot_fallback |
| Sem snapshot | 200 | **false** | degraded | degraded |

## Payload resilience (exemplo)

```json
{
  "success": true,
  "source": "snapshot",
  "resilience": {
    "mode": "snapshot_fallback",
    "reason": "live_timeout",
    "liveAttempted": true,
    "circuitStatus": "OPEN",
    "snapshotKey": "2026-06-01:2026-06-07:all"
  }
}
```

## Frontend

`fetchSales()` usa `allowDegraded: true` para não abortar UI em modo degradado auditável.
