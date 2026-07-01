# RT02_BOTTLENECK_DISCOVERY_REPORT — IA-2

**Data:** 2026-06-14

## Classificação por endpoint

| Endpoint | Gargalo RT-01 | Camada | % do tempo |
|---|---|---|---|
| `/v1/financial/overview` | Consulta live multi-filial WebPosto | **WebPosto + Gateway** | ~95% |
| `/v1/financial/expenses` | Live-first aguardando budget 22s | **WebPosto** | ~95% |
| `/v1/stock` | Loop serial N filiais × 4 endpoints | **WebPosto + Query** | ~98% |

---

## `/v1/financial/overview`

**Onde estava o atraso:** `NetworkFinancialOverviewService.get_financial_overview_only` — chamadas sequenciais WebPosto por filial.

**Classificação:** WebPosto → Gateway → Transformação (consolidação rede)

**Correção RT-02:** Snapshot-first — retorna `financial_overview` homologado sem invocar live.

---

## `/v1/financial/expenses`

**Onde estava o atraso:** `_live_with_budget` aguardava até 22s antes de fallback.

**Classificação:** WebPosto (primário) + estratégia live-first (arquitetura resiliência)

**Correção RT-02:** Snapshot-first com paginação local; live só se snapshot ausente.

---

## `/v1/stock`

**Onde estava o atraso:** `get_stock` itera todas empresas com 4 HTTP calls cada, sem timeout/circuit.

**Classificação:** WebPosto (serial) + ausência de snapshot

**Correção RT-02:**
- `StockResilienceService` (padrão P0 sales)
- `stock_circuit.py` isolado
- Kind `financial_stock` + homologação RT-02

---

## Outros (não gargalo RT-02)

| Camada | Impacto |
|---|---|
| Serialização | <5% |
| Snapshot load | <1% pós-correção |
| Frontend | Não era gargalo — aguardava API |
