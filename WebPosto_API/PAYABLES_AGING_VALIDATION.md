# PAYABLES AGING VALIDATION — F01.1.1

**Período:** 2026-06-01 → 2026-06-07

## Buckets implementados (Finance Center)

| Bucket | Qtd (rede) | Valor |
|---|---:|---:|
| vencido | 31 | R$ 140.698,76 (summary rede) |
| emAberto | — | ver API |
| aVencer | — | ver API |
| pago | — | ver API |

> **Lacuna documentada:** spec pede Vencido/Hoje/7d/15d/30d; código usa vencido/emAberto/aVencer/pago. Paridade interna **0,00** nos buckets existentes.

## Paridade API ↔ Export (caso A)

| Camada | Δ valor | Status |
|---|---|---|
| summary vs payables | 0,00 | ✅ |
| tabela vs CSV (aging CP) | 0,00 | ✅ Playwright F01.1 |
| tabela vs PDF | 0,00 | ✅ (mesmo dataset) |
| API vs snapshot | 0,00 | ✅ após HIT |

## Casos multiselect

| Caso | CP vencido (qtd) | Paridade |
|---|---:|---|
| A Todos | 31 | ✅ |
| B 11495 | 20 | ✅ |
| C 5555 | 11 | ✅ |
| D 11495,5555 | 31 | ✅ |
| E Selecionar Tudo | 31 | ✅ |
| F Limpar | 31 | ✅ |
