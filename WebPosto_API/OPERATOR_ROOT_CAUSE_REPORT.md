# OPERATOR ROOT CAUSE REPORT — F02.1-B

**Período:** 7d · **Evidência:** `scripts/f02_1b_root_cause.json`

## Operadores (estatísticas completas)

| Op | N | Soma | Média | Mediana | σ | Min | Max | P95 | P99 | Risco |
|----|---|------|-------|---------|---|-----|-----|-----|-----|-------|
| 294273 | 3 | R$ -252,27 | R$ -84,09 | R$ -46,53 | R$ 97,10 | R$ -194,36 | R$ -11,38 | R$ -14,90 | R$ -12,08 | **MÉDIO** |
| 299151 | 1 | R$ -215,77 | R$ -215,77 | R$ -215,77 | R$ 0,00 | R$ -215,77 | R$ -215,77 | R$ -215,77 | R$ -215,77 | **MÉDIO** |
| 299371 | 1 | R$ -116,80 | R$ -116,80 | R$ -116,80 | R$ 0,00 | R$ -116,80 | R$ -116,80 | R$ -116,80 | R$ -116,80 | **BAIXO** |
| 227386 | 3 | R$ -110,54 | R$ -36,85 | R$ -50,66 | R$ 29,86 | R$ -57,30 | R$ -2,58 | R$ -7,39 | R$ -3,54 | **MÉDIO** |
| 158924 | 5 | R$ -94,08 | R$ -18,82 | R$ -2,01 | R$ 171,00 | R$ -272,07 | R$ 208,96 | R$ 167,81 | R$ 200,73 | **ALTO** |
| 276288 | 6 | R$ 17,81 | R$ 2,97 | R$ -0,53 | R$ 14,82 | R$ -12,66 | R$ 28,86 | R$ 24,15 | R$ 27,92 | **MÉDIO** |
| 178278 | 2 | R$ 2,79 | R$ 1,40 | R$ 1,40 | R$ 1,10 | R$ 0,62 | R$ 2,17 | R$ 2,09 | R$ 2,15 | **BAIXO** |

## Focus 276288 (recorrência 90d F02.1-A)

| Métrica | Valor |
|---------|-------|
| Fechamentos | 6 |
| Diff acumulada | R$ 17,81 |
| Média / Mediana | R$ 2,97 / R$ -0,53 |
| P95 / P99 | R$ 24,15 / R$ 27,92 |
| Risco | **MÉDIO** |

## Focus 294273 (maior diff acumulada 7d)

| Métrica | Valor |
|---------|-------|
| Fechamentos | 3 |
| Diff acumulada | R$ -252,27 |
| Média / Mediana | R$ -84,09 / R$ -46,53 |
| P95 / P99 | R$ -14,90 / R$ -12,08 |
| Risco | **MÉDIO** |

**Classificação:** BAIXO · MÉDIO · ALTO · CRÍTICO — critério `|sum|`, recorrência e P99 (script audit).
