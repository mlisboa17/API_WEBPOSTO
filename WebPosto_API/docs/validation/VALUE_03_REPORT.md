# VALUE-03 — Runtime Validation Report

**Executado:** 2026-07-04

## Fase 2 — Dados reais

Arquivo: `VALUE_03_EXPENSE_DATA_RAW.json`

| Tenant | Registros atual | Registros baseline | Total atual | Total baseline |
|---:|---:|---:|---:|---:|
| 5555 | 192 | 274 | R$ 29.117,31 | R$ 54.821,17 |
| 11495 | 296 | 359 | R$ 72.249,93 | R$ 129.531,49 |
| 74014 | 154 | 118 | R$ 44.940,40 | R$ 49.307,88 |

Período atual: 2026-06-05 → 2026-07-04  
Baseline: 2026-05-06 → 2026-06-04

## Fase 8 — Discovery Engine

Arquivo: `VALUE_03_DISCOVERY_RAW.json`

| tenant | detector | candidate_type | impact | confidence | priority | final_state |
|---|---|---|---:|---:|---:|---|
| 74014 | ExpenseDetector | CATEGORY_SPIKE | 11251.5 | 0.89 | 52.63 | DECISION |

**Decisions:** 1 | **Observations:** 0 | **Discarded:** 0

**Vencedor global:** ExpenseDetector (74014) — único candidato acima dos thresholds (impact ≥ R$ 5.000, confidence ≥ 80%).

FuelRevenueDetector: executado nos 3 tenants, sem candidato no período de 7 dias da análise Home.

## Performance

| Métrica | Valor |
|---|---|
| FULL_ANALYSIS_COLD | 59,9 s |
| FULL_ANALYSIS_WARM | 2,3 ms |
| HOME_RESPONSE_MS | 2,6 ms |
| REFRESH_TRIGGER_MS | 15,9 ms |
| expense cache hits/misses (warm run) | 3 / 3 |
| fuel cache hits/misses (warm run) | 3 / 3 |

Cold aumentou vs PERFORMANCE-01 (~47s) por chamadas `CONSULTAR_DESPESAS_FINANCEIRO_REDE` (~18s/tenant).

## Isolamento

- Cache expense isolado por tenant + período: **PASS**
- Single-flight (PERFORMANCE-01): **PASS** (não revalidado nesta sprint)

## Limitações

- Fornecedor vazio em TITULO_PAGAR nos 3 postos (SUPPLIER_SPIKE inativo).
- Categorias são textos livres (`planoConta`), não plano contábil normalizado.
- VALUE_OUTLIER e CROSS_TENANT não implementados.
