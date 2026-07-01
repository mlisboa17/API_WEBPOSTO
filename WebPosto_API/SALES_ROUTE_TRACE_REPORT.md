# SALES_ROUTE_TRACE_REPORT — HOTFIX P0

## Fluxo mapeado

```text
GET /v1/sales
  → fechamento_enterprise.sales()
  → SalesResilienceService.get_sales()
       ├─ sales_circuit_open() ? snapshot/degraded (circuit_open)
       ├─ _attempt_live(timeout=8s)
       │    └─ NetworkFinancialOverviewService.get_sales()
       │         ├─ _resolve_empresas() → get_companies() → WebPosto EMPRESAS
       │         └─ for empresa in empresas:
       │              _fetch_vendas_produtos()
       │                ├─ call_endpoint("venda")
       │                ├─ _collect_with_cursor("venda_item_rede", "venda_item") [até 10 páginas]
       │                └─ _collect_with_cursor("venda_forma_pagamento_rede", ...) [até 10 páginas]
       │                    └─ WebPostoClient.call_endpoint() → httpx.AsyncClient.get + retry_async(3)
       ├─ save_kind("financial_sales") se live OK
       └─ load_kind("financial_sales") fallback paginado
```

## Função que bloqueava

| Camada | Função | Bloqueio |
|---|---|---|
| Gateway | `WebPostoClient.call_endpoint` | Async real, porém timeout httpx 20–30s × retry 3 × múltiplas páginas |
| Service | `_fetch_vendas_produtos` | Sequencial: 1 + até 20 chamadas cursor por filial |
| Service | `get_sales` | Loop sequencial por **todas** as filiais |
| Resilience (antes) | `asyncio.wait_for(22s)` | Cancelamento não garantia resposta <22s em carga real |

## Respostas IA-1

| Pergunta | Resposta |
|---|---|
| Qual função bloqueia? | Cadeia `_fetch_vendas_produtos` + multi-filial em `get_sales` |
| É async real? | Sim (`httpx.AsyncClient`, `await`) |
| Existe `requests` síncrono? | **Não** no fluxo sales |
| Timeout aplicado? | httpx 20s+ por call; orçamento P0: **8s live / 22s total** |

## Correção aplicada

Novo serviço dedicado: `src/services/sales_resilience_service.py`
