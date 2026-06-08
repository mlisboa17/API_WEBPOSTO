# SCREEN_HEALTH_A03_6

| Tela | Status | ms médio | Issues |
|---|---|---:|---|
| executive | **OK** | 8990.9 | — |
| dashboard | **OK** | 3391.1 | — |
| expenses | **OK** | 3101.2 | — |
| accounts | **OK** | 3864.0 | — |
| sales | **OK** | 10623.0 | — |
| stock | **OK** | 4337.6 | — |
| fuels | **PARCIAL** | 6830.9 | /api/v1/sales/fuel-summary: sem dados |
| financial | **PARCIAL** | 850.8 | /api/v1/financial/snapshot: sem dados |

## Snapshots (2ª chamada)

- **executive**: hit=MISS/LIVE, call1=5.3ms, call2=4.0ms
- **fuel**: hit=MISS/LIVE, call1=5.2ms, call2=4.4ms
- **financial**: hit=MISS/LIVE, call1=4.1ms, call2=4.0ms

## Performance média

- executive: avg=8990.9ms, max=14659.2ms
- dashboard: avg=3391.1ms, max=3391.1ms
- expenses: avg=3101.2ms, max=3101.2ms
- accounts: avg=3864.0ms, max=3864.0ms
- sales: avg=10623.0ms, max=10623.0ms
- stock: avg=4337.6ms, max=4337.6ms
- fuels: avg=6830.9ms, max=11500.4ms
- financial: avg=850.8ms, max=1693.1ms
