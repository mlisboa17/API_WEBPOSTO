# RT02_ENDPOINT_TRACE_REPORT — IA-1

**Data:** 2026-06-14 | **Período:** 2026-06-01 → 2026-06-07 | **Evidência:** `scripts/rt02_performance_results.json`

## Resumo antes / depois

| Endpoint | RT-01 | RT-02 | Modo |
|---|---|---|---|
| `/v1/financial/overview` | 33,71s | **0,02s** | `snapshot_first` |
| `/v1/financial/expenses` | 22,14s | **0,01s** | `snapshot_first` |
| `/v1/stock` | 44,94s | **0,02s** | `snapshot_first` |
| `/v1/sales` | 8,02s | **8,02s** | `snapshot_fallback` (P0 mantido) |

---

## Trace `/v1/financial/overview`

| Camada | RT-01 (live-first) | RT-02 (snapshot-first) |
|---|---|---|
| HTTP route | ~0ms | ~0ms |
| FinancialResilienceService | live imediato | **load snapshot** |
| WebPosto gateway | **~30–33s** multi-filial | **0s** (não invocado) |
| Snapshot disco | fallback após live | **~10–20ms** |
| Serialização JSON | ~50ms | ~10ms |
| **Total** | **33,7s** | **0,02s** |

**Rota:** `fechamento_enterprise.financial_overview` → `FinancialResilienceService.get_financial_overview`

---

## Trace `/v1/financial/expenses`

| Camada | RT-01 | RT-02 |
|---|---|---|
| Resilience | live 22s budget | **snapshot_first** |
| WebPosto | **~22s** | **0s** |
| Snapshot + paginação | após timeout | **~10ms** |
| **Total** | **22,1s** | **0,01s** |

**Rota:** `financial_expenses` → `get_financial_expenses` com paginação local

---

## Trace `/v1/stock`

| Camada | RT-01 | RT-02 |
|---|---|---|
| Route | `_network_financial_overview.get_stock` direto | `StockResilienceService.get_stock` |
| WebPosto | **4 calls × N filiais serial** (~45s) | **0s** com snapshot |
| Snapshot | inexistente | `financial_stock` homologado |
| Circuit stock | inexistente | `stock_circuit` isolado |
| **Total** | **44,9s** | **0,02s** |

**Endpoints WebPosto por filial (RT-01):** `produto_estoque`, `produto`, `tanque`, `estoque_periodo`

---

## Frontend (estimado)

| Tela | Timeout UX | RT-02 impacto |
|---|---|---|
| Receitas | 45s | Carrega em **<1s** |
| Despesas | 45s | Carrega em **<1s** |
| Tanques | 30s | Carrega em **<1s** |

Frontend não alterado — ganho vem da API.
