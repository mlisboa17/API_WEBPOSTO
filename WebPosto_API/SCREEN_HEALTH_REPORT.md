# SCREEN_HEALTH_REPORT — Sprint P0

**Gerado:** 2026-06-08T13:00:19

| Tela | Classificação | Issues |
|---|---|---|
| executive | **PARCIAL** | /api/v1/executive/snapshot: HTTP 200 sem dados; /api/v1/network/coverage: HTTP 200 sem dados |
| fuels | **PARCIAL** | /api/v1/fuel/snapshot: HTTP 200 sem dados; /api/v1/sales/fuel-summary: HTTP 200 sem dados |
| sales | **OK** | — |
| expenses | **OK** | — |
| accounts | **OK** | — |
| stock | **OK** | — |
| dashboard | **OK** | — |

## Detalhe por endpoint

### EXECUTIVE
- `/api/v1/executive/snapshot`: HTTP 200, 8.7ms, rows=0, snapshot=False
- `/api/v1/kpis`: HTTP 200, 9490.1ms, rows=0, snapshot=None
- `/api/v1/dre`: HTTP 200, 8540.2ms, rows=0, snapshot=None
- `/api/v1/data-quality`: HTTP 200, 18926.1ms, rows=0, snapshot=None
- `/api/v1/network/coverage`: HTTP 200, 543.3ms, rows=0, snapshot=None

### FUELS
- `/api/v1/fuel/executive`: HTTP 200, 1647.0ms, rows=0, snapshot=None
- `/api/v1/fuel/snapshot`: HTTP 200, 3.8ms, rows=0, snapshot=False
- `/api/v1/sales/fuel-summary`: HTTP 200, 8421.4ms, rows=0, snapshot=None

### SALES
- `/v1/sales`: HTTP 200, 7933.4ms, rows=50, snapshot=None

### EXPENSES
- `/v1/financial/expenses`: HTTP 200, 1338.8ms, rows=71, snapshot=None

### ACCOUNTS
- `/v1/financial/accounts-payable`: HTTP 200, 1200.1ms, rows=50, snapshot=None

### STOCK
- `/v1/stock`: HTTP 200, 3372.3ms, rows=11, snapshot=None

### DASHBOARD
- `/v1/financial/overview`: HTTP 200, 1878.7ms, rows=0, snapshot=None

