# Audit Expenses WebPosto — Resultado

**Gerado:** 2026-06-08T12:56:22
**Período:** 2026-06-01 .. 2026-06-07
**Empresa:** 11495

## Comparação

| Fonte | Registros | Valor Total | Observação |
|---|---:|---:|---|
| API bruta (paginada ultimoCodigo) | 427 | 135761.20 | Referência máxima |
| API bruta (página única) | 427 | 135761.20 | Como backend hoje |
| Após normalização+dedupe | 383 | 123899.40 | Simulação backend |
| Backend LOGOS | 71 | 24676.71 | total API=71 |
| Frontend tabela | = Backend | — | fetchAllPages sobre /v1/financial/expenses |
| Export CSV/PDF | = Tabela filtrada | — | sortedRows em export.js |

## Diagnóstico

- **[P0]** api_ignora_empresaCodigo: API retorna 427 (rede); backend filtra 11495 → 71 (**correto para single**).
- **[P0]** multiselect_backend: `11495,5555` retorna 415 (10 filiais) — ver FILTER_AUDIT_REPORT.md.
- **[P2]** deduplicacao: 44 registros removidos por _dedupe_rows (visão rede).

## Registros perdidos

- paginacao: **0**
- backend_vs_api: **356**
- normalizacao: **0**
- dedupe: **44**

## Correção recomendada

3. Validar token por filial (5256, 5333, etc.).
