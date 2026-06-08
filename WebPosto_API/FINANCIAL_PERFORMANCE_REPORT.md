# FINANCIAL_PERFORMANCE_REPORT — A03.7

| Endpoint | HTTP | ms | Registros |
|---|---|---:|---:|
| MOVIMENTO_CONTA | 200 | 486.2 | 200 |
| CAIXA | 200 | 161.6 | 21 |
| CAIXA_APRESENTADO | 200 | 144.6 | 21 |
| TITULO_PAGAR | 200 | 169.6 | 70 |
| TITULO_RECEBER | 200 | 152.1 | 11 |
| DESPESAS_REDE | 200 | 2016.1 | 432 |
| TRANSFERENCIA_BANCARIA | 200 | 3954.0 | 200 |

## Observações

- DESPESAS: 1 fetch rede (P0.2) — ~500-1200ms
- MOVIMENTO/TRANSFERENCIA: paginar ultimoCodigo
- Snapshot LOGOS: MISS/LIVE (A03.6) — implementar warm cache F01
- TITULO_PAGAR overview: N× filial — otimizar em F01
