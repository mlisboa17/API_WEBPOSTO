# LOGOS SPACE — Architecture Baseline 2.0

**Data:** 2026-06-08 · Pós F01.4-D

## Entrypoint oficial

- `src/main.py` → porta **8040** → `/app/financial`

## Serviços financeiros oficiais

| Serviço | Arquivo |
|---------|---------|
| Finance Center | `corporate_finance_center_service.py` |
| Cash Flow | `corporate_cash_flow_service.py` |
| Intelligence | `financial_intelligence_service.py` |
| Advanced F01.4-B | `financial_intelligence_advanced_service.py` |
| Health Score V3 | `financial_health_score_v3_service.py` |
| Supplier Intelligence | `supplier_intelligence_service.py` |
| Supplier Segmentation | `supplier_segmentation_service.py` |
| Network Overview | `network_financial_overview_service.py` |

## Snapshots ativos (TTL 300s)

- `finance_center_snapshot_service.py`
- `finance_intelligence_snapshot_service.py` (intelligence + advanced + health V3 + suppliers + segmentation)
- `cash_flow_snapshot_service.py`

## APIs oficiais

| Prefixo | Router |
|---------|--------|
| `/api/v1/finance/center/*` | `finance_center.py` |
| `/api/v1/finance/cash-flow/*` | `cash_flow.py` |
| `/api/v1/finance/intelligence/*` | `financial_intelligence.py` |

## Dashboards ativos

- `view=finance-center` — FC + Intelligence + Supplier + Segmentation
- `view=cash-flow`

## Nota arquitetural

**9.6/10** — camada financeira corporativa consolidada F01.1→F01.4-D.

## Risco arquitetural

**14/100** — duplicidade histórica de clientes WebPosto e entrypoints legados (8050).
