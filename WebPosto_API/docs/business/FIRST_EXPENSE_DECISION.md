# Primeira Decisão de Despesa — VALUE-03

**Data:** 2026-07-04  
**Tenant:** 74014 — POSTO DOZE FILIAL II  
**Detector:** ExpenseDetector

## Decisão

**Título:** R$ 7.501 acima do comportamento de referência em *Vale de funcionário referente a consolidação de caixa*

## Evidência

| Métrica | Atual (30d) | Baseline (30d anterior) |
|---|---:|---:|
| Valor categoria | R$ 8.401,00 | R$ 900,00 |
| Excesso estimado | R$ 7.501,00 | — |
| Lançamentos | 16 | 7 |

## Money Found

- **at_risk:** R$ 7.501,00 — `ESTIMATED`
- **recoverable:** R$ 3.750,50 — `ESTIMATED`

## Confidence

- Detector: **89%** (≥ 80% → DECISION)
- Priority Score: **52,63**

## Causa provável (ExpenseRootCause)

Maior volume de lançamentos na categoria *Vale de funcionário referente a consolidação de caixa* (16 vs 7 no baseline).

## Recomendações

1. Revisar os 5 maiores lançamentos da categoria no período.
2. Validar se correspondem a vales/consolidações reais de caixa.

## Honestidade

Não é perda confirmada. Pode refletir operação legítima (mais turnos, consolidações). Requer conferência documental.
