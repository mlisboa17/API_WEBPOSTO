# CASH OPERATION AUDIT — F01.1.1

**Período:** 2026-06-01 → 2026-06-07

## Agregados CAIXA + CAIXA_APRESENTADO

| Métrica | Valor |
|---|---:|
| Turnos | 21 |
| Turnos com diferença | 21 |
| Despesa caixa (apurado) | R$ 4949.67 |
| Vale funcionário (apurado) | R$ 19879.91 |
| Empréstimos (apurado) | R$ 0.00 |

## Top filiais — diferença de caixa

| Filial | Turnos c/ diff | Σ |dif| |
|---|---:|---:|
| 5555 | 6 | R$ 17918.36 |
| 11495 | 15 | R$ 544.11 |

## Campos auditados

- `despesaApurado`, `valeFunApurado`, `emprestimoApurado` — somados por turno em CAIXA_APRESENTADO
- `diferenca` — CAIXA bruto por turno

## Riscos operacionais

- **100%** dos turnos (21/21) apresentam diferença ≠ 0 — prioridade F03 Operação de Caixa.
- Filial **5555** concentra **97%** do valor absoluto de diferenças.
