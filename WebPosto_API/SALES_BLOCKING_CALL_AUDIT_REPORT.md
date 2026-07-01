# SALES_BLOCKING_CALL_AUDIT_REPORT — HOTFIX P0

## Escopo auditado

Arquivos: `fechamento_enterprise.py`, `sales_resilience_service.py`, `network_financial_overview_service.py`, `webposto_client.py`, `retry.py`

| Local | Chamada | Classificação |
|---|---|---|
| `webposto_client.call_endpoint` | `await httpx.AsyncClient.get` | **ASYNC_OK** |
| `webposto_client.call_endpoint` | `response.json()` | **ASYNC_OK** (CPU leve) |
| `retry.py` | `await asyncio.sleep` | **ASYNC_OK** |
| `network_financial_overview.get_sales` | loops sync sobre rows | **ASYNC_OK** (não bloqueia I/O) |
| `_fetch_vendas_produtos` | até 41 awaits sequenciais | **UNKNOWN** (async mas latência acumulada) |
| `discover_permissions` | probe paralelo | **ASYNC_OK** |

## Não encontrado no fluxo sales

- `requests.get` — ausente
- `time.sleep` — ausente (usa `asyncio.sleep`)
- `subprocess` — ausente
- Cliente síncrono — ausente

## Causa raiz

Não é bloqueio clássico de event loop, e sim **fan-out sequencial** com timeout alto por chamada:

```text
filiais × (venda + 10×item + 10×fp) × retry(3) × timeout(20s+) >> 22s
```

## Mitigação P0

- Orçamento live **8s** com cancelamento explícito da task
- Circuit breaker **sales** isolado (`venda` gate)
- Fallback snapshot imediato pós-timeout
