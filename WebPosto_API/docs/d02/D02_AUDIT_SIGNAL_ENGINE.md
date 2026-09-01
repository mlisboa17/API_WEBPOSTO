# D02 — Audit Signal Engine (Agente 7)

> Sinais **após** divergência interna — revisão recomendada, não acusação. Auditoria externa só com evidência bancária/adquirente/comprovante. [D02_CONCEPTUAL_CORRECTION.md](./D02_CONCEPTUAL_CORRECTION.md)

## Implementação

`src/services/cash_reconciliation/audit_signal_engine.py`

## Sinais determinísticos

| signalType | Gatilho | Linguagem |
|---|---|---|
| UNJUSTIFIED_DIVERGENCE | dif ≠ 0 sem justificativa | DIVERGÊNCIA RECORRENTE — revisão recomendada |
| THRESHOLD_EXCEEDED | |dif| ≥ limite (default R$ 100) | DIVERGÊNCIA acima do limite |
| RECURRING_NATURE | mesma natureza ≥ 2× | PADRÃO RECORRENTE |
| RECURRING_CAIXA | mesmo caixa ≥ 2× | PADRÃO RECORRENTE |
| EXCESSIVE_OTHER | OTHER > 35% justificativas | revisão recomendada |
| OVERDUE_OPEN | prazo resolução vencido | EVIDÊNCIA AUSENTE |

## Severidades

INFO | LOW | MEDIUM | HIGH | CRITICAL

## Proibições

- Sem IA generativa
- Sem acusação de fraude
- Sem rotular funcionário suspeito
