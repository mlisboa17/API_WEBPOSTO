# Catálogo de Endpoints WebPosto - SPRINT 21.3

Este documento cataloga os endpoints auditados, sua classificação e onde são utilizados no sistema.

## PRODUCAO

| Endpoint | Status | Tempo (ms) | Utilizado Por |
|----------|--------|------------|---------------|
| `/health` | 200 | 5528 | N/A (Infra) |
| `/ready` | 200 | 1757 | N/A (Infra) |
| `/metrics/stream` | 200 | 1763 | N/A |
| `/api/v1/filiais` | 200 | 8797 | filiais.js, app.js |

## EXPERIMENTAL

| Endpoint | Status | Tempo (ms) | Utilizado Por |
|----------|--------|------------|---------------|
| *Nenhum endpoint nesta categoria* | | |

## OBSOLETO

| Endpoint | Status | Tempo (ms) | Utilizado Por |
|----------|--------|------------|---------------|
| `/auditoria/health` | 404 | 1325 | N/A |
| `/auditoria/despesas/real_01` | 404 | 1319 | N/A |
| `/auditoria/fechamentos/real_01` | 404 | 1322 | N/A |
| `/auditoria/resumo/real_01` | 404 | 1323 | N/A |
| `/clientes/` | 500 | 5503 | N/A |
| `/clientes/1` | 500 | 5464 | N/A |
| `/expenses/extract` | 500 | 1748 | N/A |
| `/metrics/executive` | 401 | 1761 | executiveDashboard.js |
| `/sync/clientes` | 500 | 6741 | N/A |
| `/sync/abastecimentos` | 500 | 6706 | N/A |
| `/sync/financeiro` | 500 | 8302 | N/A |
| `/sync/caixa` | 500 | 8300 | N/A |
| `/sync/full` | 500 | 8271 | N/A |
| `/auth/login` | 422 | 5060 | auth.js |
| `/v1/financial/expenses` | 422 | 5072 | expenses.js, app.js |
| `/v1/financial/accounts-payable` | 422 | 5093 | accountsPayable.js, app.js |
| `/v1/sales` | 422 | 5101 | sales.js, app.js |
| `/v1/stock` | 422 | 5109 | stock.js, app.js |
| `/v1/financial/overview` | 422 | 5117 | executiveDashboard.js, app.js |
| `/v1/companies` | 404 | 5461 | N/A |
| `/api/v1/kpis` | 422 | 5463 | executiveDashboard.js, analyticsEngine.js |
| `/api/v1/dre` | 422 | 5493 | executiveDashboard.js, analyticsEngine.js |
| `/api/v1/data-quality` | 422 | 5508 | executiveDashboard.js |
| `/api/v1/network-coverage` | 404 | 5527 | N/A |
| `/EMPRESAS` | 404 | 6462 | N/A |
| `/VENDA` | 404 | 6465 | N/A |
| `/VENDA_ITEM` | 404 | 6468 | N/A |
| `/VENDA_FORMA_PAGAMENTO` | 404 | 6468 | N/A |
| `/CONSULTAR_DESPESAS_FINANCEIRO_REDE` | 404 | 6469 | N/A |
| `/TITULO_PAGAR` | 404 | 6470 | N/A |
| `/TITULO_RECEBER` | 404 | 6471 | N/A |
| `/CONSULTAR_CAIXA_REDE` | 404 | 6473 | N/A |
| `/CONSULTAR_CAIXA_APRESENTADO_REDE` | 404 | 6473 | N/A |
| `/PRODUTO_EMPRESA` | 404 | 6474 | N/A |
| `/PRODUTO_ESTOQUE` | 404 | 6475 | N/A |

