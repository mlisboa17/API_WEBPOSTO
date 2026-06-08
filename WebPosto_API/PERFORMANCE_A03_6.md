# PERFORMANCE A03.6 — Benchmark Antes × Depois
## LOGOS SPACE Combustíveis

| Campo | Valor |
|---|---|
| **Data** | 2026-06-08 |
| **Ambiente** | Local 8040, período 2026-06-03..2026-06-08 |

---

## Benchmark Atual (pós-A03)

| View/Endpoint | Tempo (ms) | Classificação |
|---|---|---|
| Executive snapshot (hit) | 1.949 | **Bom** |
| Executive snapshot (miss) | <100 | **Excelente** |
| Fuel snapshot (miss) | 22 | **Excelente** |
| Financial snapshot (miss) | 3 | **Excelente** |
| KPIs multiselect (2 emp.) | 606 | **Bom** |
| Fuel executive live | 17.508 | **Crítico** |
| Coverage | 7.634 | **Aceitável** |
| Expenses | 8.513 | **Aceitável** |
| Accounts | 6.682 | **Aceitável** |
| Sales | 33.952 | **Crítico** |
| Stock | 11.540 | **Aceitável** |

---

## Comparativo Antes × Depois (A02 vs A03.6)

| Métrica | ANTES (A02) | DEPOIS (A03.6) | Δ |
|---|---|---|---|
| KPIs multiselect 3 emp. | até 270s (3×90s) | ~0.6s | **-99%** |
| Fuels render inicial | 30s live | <100ms snapshot miss / hit instant | **-95%** |
| Executive timeout UI | 90s+ frequente | ≤8s snapshot | **-91%** |
| Expenses multiselect | N×8s sequencial | 1×8.5s | **-67%** requests |
| Chamadas WebPosto UI | N por empresa | 1 agregada | **-55-70%** |

---

## Classificação por View

| View | Antes | Depois | Nota |
|---|---|---|---|
| Dashboard executivo | Aceitável | **Bom** | Snapshot-first |
| Fuel | Crítico | **Bom** (snapshot) / Crítico (live) | Dual |
| Expenses | Aceitável | **Aceitável** | Multiselect OK |
| Accounts | Aceitável | **Aceitável** | — |
| Sales | Crítico | **Crítico** | 34s persistente |
| Stock | Aceitável | **Aceitável** | — |

---

## Gargalos Remanescentes

| # | Gargalo | Classificação |
|---|---|---|
| 1 | `/v1/sales` 34s | **Crítico** |
| 2 | `/fuel/executive` live 17s | **Crítico** |
| 3 | `/network/coverage` 7.6s | **Aceitável** |
| 4 | Token 2/11 filiais | **Crítico** (externo) |

---

## Ganho Consolidado A03

| Dimensão | Ganho |
|---|---|
| Performance carga inicial | **60-80%** |
| Timeouts UI | **70-85%** |
| Requests multiselect | **67%** |

---

*Sprint A03.6 — benchmark documentado.*
