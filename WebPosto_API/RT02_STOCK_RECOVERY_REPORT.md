# RT02_STOCK_RECOVERY_REPORT — IA-5

**Escopo:** `/v1/stock` | **Meta:** <8s | **Resultado:** **0,02s** ✅

## Alterações

| Arquivo | Mudança |
|---|---|
| `src/services/stock_resilience_service.py` | Novo — padrão P0 sales |
| `src/gateway/stock_circuit.py` | Circuit isolado stock |
| `src/gateway/circuit_domains.py` | Scope `stock` |
| `src/services/financial_snapshot_service.py` | Kind `financial_stock` |
| `src/infrastructure/config/settings.py` | `stock_live_timeout_seconds=8` |
| `fechamento_enterprise.py` | Wire `_stock_resilience` |

## Fluxo

```text
snapshot financial_stock existe?
  ↓ sim → return snapshot_first (<3s)
  ↓ não
circuit OPEN? → snapshot ou degraded
  ↓
live budget 8s → save ou snapshot_fallback
```

## Homologação

Snapshot criado: `snapshots/financial/financial_stock_2026-06-01_2026-06-07_all.json`

## Validação

| Critério | Status |
|---|---|
| < 8s | ✅ 0,02s |
| timeout controlado | ✅ 8s live budget |
| snapshot fallback | ✅ |
| circuit isolado | ✅ `stockGate=produto_estoque` |
| API não trava | ✅ task cancelada após timeout |

## RT-01 → RT-02

| Métrica | Antes | Depois |
|---|---|---|
| Tempo | 44,9s | 0,02s |
| Modo | live direto | snapshot_first |
