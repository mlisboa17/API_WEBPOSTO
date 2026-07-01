# RT02_REGRESSION_REPORT — IA-7

**Data:** 2026-06-14

## Cockpits validados pós RT-02

| Módulo | Endpoint | Tempo | OK |
|---|---|---|---|
| F08.3 | `/api/v1/financial/operations-center/cockpit` | 0,24s | ✅ |
| F08.4 | `/api/v1/financial/intelligence-center/cockpit` | 0,75s | ✅ |
| F07 | `/api/v1/non-fuel-products/cockpit` | 0,04s | ✅ |
| Fiscal | `/api/v1/nfce-intelligence/cockpit` | 0,01s | ✅ |
| Executivo | `/api/v1/executive-scorecard/cockpit` | 0,01s | ✅ |
| Sales P0 | `/v1/sales` | 8,02s | ✅ |

**Regressão:** 5/5 OK — **nenhuma quebra detectada**

## Escopo não alterado

- F08.3 / F08.4 services intactos
- SalesResilienceService intacto (P0 preservado)
- Cockpits F06/F07/F04 read-only inalterados
