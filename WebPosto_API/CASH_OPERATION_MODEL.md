# CASH_OPERATION_MODEL — A03.7

**Turnos auditados:** 21

## Matriz operação de caixa

| Conceito | Campo API | Disponível | Evidência período |
|---|---|---|---|
| Despesa caixa | despesaApurado/Diferenca | **Sim** | R$ 4949.67 apurado |
| Vale funcionário | valeFunApurado/Diferenca | **Sim** | R$ 19879.91 |
| Empréstimo | emprestimoApurado/Diferenca | **Sim** | R$ 0.00 |
| Quebra/diferença | diferenca (CAIXA) | **Sim** | média 1093.16 |
| Sangria explícita | — | **Não** | via DESPESAS_REDE se lançada |
| Suprimento | — | **Não** | — |
| Fundo caixa | — | **Não** | — |

## Modelo LOGOS

```
fact_caixa_turno       ← CAIXA
fact_caixa_forma       ← CAIXA_APRESENTADO
fact_despesa_gerencial ← DESPESAS (lançamentos plano — separado)
```
