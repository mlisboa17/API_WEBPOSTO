# SALES_CIRCUIT_BREAKER_REPORT — HOTFIX P0

## Escopo isolado

Arquivo: `src/gateway/sales_circuit.py`

Endpoints monitorados:

```text
venda (gate)
venda_item / venda_item_rede
venda_forma_pagamento / venda_forma_pagamento_rede
```

## Domínio admin

`CIRCUIT_SCOPES["sales"]` adicionado em `circuit_domains.py` — **separado** de `financial` (`despesas_financeiro_rede`).

## Comportamento

| Evento | Ação |
|---|---|
| Live timeout | `record_sales_live_failure()` → block `venda` + failures nos demais |
| Circuit OPEN | `get_sales` pula live, usa snapshot |
| HALF_OPEN | Permite nova tentativa live após TTL |

## Status exposto

`resilience.circuitStatus` usa `sales_circuit_status()` — não reutiliza `_circuit_for_financial()`.
