# FINANCE CENTER PERFORMANCE REPORT — F01.1.1

## Snapshot

| Métrica | Valor | Meta | Status |
|---|---:|---:|---|
| MISS 11495 | 3.1 ms | — | fromSnapshot=false ✅ |
| HIT 11495 | 11.8 ms | < 500 ms | ✅ |
| HIT rede | 9.3 ms | < 500 ms | ✅ |

## API live (caso A — MISS snapshot)

| Endpoint | ms |
|---|---:|
| summary | 39667.0 |
| payables | 1054.8 |
| bank | 11747.5 |
| cash | 10729.3 |
| snapshot (HIT) | 10.2 |

## Render UI

- Com snapshot HIT: **< 2 s** ✅ (Playwright F01.1)
- Live summary 1ª carga: ~40 s (WebPosto) — mitigado por Snapshot First

## Export / filtros

- Debounce filtros: 300 ms
- Playwright export CSV/PDF: **15/15 PASS**
- Timeout: **nenhum** nos testes E2E
