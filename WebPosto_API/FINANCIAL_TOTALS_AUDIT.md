# FINANCIAL TOTALS AUDIT — Sprint A03.6
## LOGOS SPACE Combustíveis

| Campo | Valor |
|---|---|
| **Data** | 2026-06-08 |
| **Período teste** | 2026-06-03 .. 2026-06-08 |
| **Empresa** | 11495 (POSTO VIP) |

---

## Metodologia

Prova matemática em 3 camadas:

1. **Autosoma tabela** — `buildSumMap()` em `table.js` (colunas `sum: true`)
2. **Export CSV/PDF** — `downloadCsv` / `openPdfPreview` usam `sortedRows` (mesmo dataset)
3. **Cross-check API** — soma backend vs KPIs executive snapshot

**Regra:** Tabela = CSV = PDF para linhas visíveis filtradas → diferença **0**.

---

## Resultados por Tabela

### Expenses

| Métrica | Valor | Status |
|---|---|---|
| Linhas API | 45 | — |
| Total paginação (count) | 45 | **PASSOU** |
| Autosoma valor (página completa) | R$ 13.810,23 | — |
| KPI executive `despesasTotais` | R$ 13.810,23 | **PASSOU** (Δ=0) |
| Tabela = CSV = PDF | Mesmo `sortedRows` | **PASSOU** |

### Accounts Payable

| Métrica | Valor | Status |
|---|---|---|
| Linhas API | 41 | — |
| Total paginação | 41 | **PASSOU** |
| Tabela = CSV = PDF | Mesmo pipeline | **PASSOU** |
| Cross-check KPI | N/A (contas ≠ despesas totais) | — |

### Sales

| Métrica | Valor | Status |
|---|---|---|
| Linhas API (limit 500) | 200 | — |
| Total paginação | 200 | **PASSOU** |
| Tempo resposta | ~34s | **RISCO** performance |
| Tabela = CSV = PDF | Mesmo pipeline | **PASSOU** |
| Autosoma monetário | Campo `valorTotal` inconsistente em linhas | **RISCO** |

### Stock

| Métrica | Valor | Status |
|---|---|---|
| Linhas API | 11 | — |
| Total paginação | 11 | **PASSOU** |
| Tabela = CSV = PDF | Mesmo pipeline | **PASSOU** |

### Fuel

| Métrica | Valor | Status |
|---|---|---|
| Litros LMC (fuel/executive) | 8.768,62 L | — |
| Combustíveis distintos | 6 | **PASSOU** |
| Litros Vendidos (fuel-summary) | Métrica comercial separada | **PASSOU** (não comparar com LMC) |
| Export fuels | Via `fuelExecutiveDashboard` | **PASSOU** |

---

## Divergências Identificadas

| # | Problema | Impacto | Status |
|---|---|---|---|
| 1 | `fetchAllPages` limit 40×200 — datasets >8000 linhas truncados | Autosoma incompleto | **RISCO** |
| 2 | Sales ~34s — usuário pode exportar antes de carga completa | Totais parciais | **RISCO** |
| 3 | Paginação UI `synthetic: true` redefine total = `merged.length` | OK se fetchAllPages completo | **PASSOU** |
| 4 | Header filter reduz linhas — autosoma recalcula filtrado | CSV = tabela filtrada | **PASSOU** (by design) |

---

## Prova Matemática — Expenses (caso referência)

```
Σ valor (45 linhas) = 13.810,23
KPI despesasTotais   = 13.810,23
Δ                    = 0,00 ✅
```

---

## Classificação

| Domínio | Tabela=CSV=PDF | Cross-check API |
|---|---|---|
| Expenses | **PASSOU** | **PASSOU** |
| Accounts | **PASSOU** | N/A |
| Sales | **PASSOU** | **RISCO** (campo valor) |
| Stock | **PASSOU** | N/A |
| Fuel | **PASSOU** | **PASSOU** (LMC isolado) |

---

*Meta Tabela=CSV=PDF atingida para linhas carregadas. Divergência zero em expenses vs KPI.*
