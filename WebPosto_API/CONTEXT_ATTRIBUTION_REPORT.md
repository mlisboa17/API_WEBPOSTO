# CONTEXT VS OPERATOR ATTRIBUTION — F03.4 · Agente 6-B

## Hipótese

```text
Um operador pode parecer excelente ou crítico porque trabalha sempre no mesmo PDV, turno ou filial.
```

## Fórmula

```text
contextAdjustedPerformanceScore = operatorPerformanceScore - contextRiskPenalty + multiContextBonus
```

## Perguntas obrigatórias

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Melhores operadores sempre nos mesmos PDVs? | **True** |
| 2 | Piores operadores sempre nos mesmos PDVs? | **True** |
| 3 | Melhores operadores sempre nos mesmos turnos? | **True** |
| 4 | Piores operadores sempre nos mesmos turnos? | **True** |
| 5 | Operador bom em PDV ruim? | **[]** |
| 6 | Operador ruim em PDV bom? | **[]** |
| 7 | PDV prejudica operadores? | **[15880, 54193]** |
| 8 | Turno prejudica operadores? | **[]** |
| 9 | Operador consistente multi-contexto? | **[]** |
| 10 | Operador dependente de contexto? | **299151, 294273, 178278, 158924, 276288** |

## Casos obrigatórios

| Caso | Score bruto | Score ajustado | Classificação | PDV dominante |
|------|-------------|----------------|---------------|---------------|
| Operador 276288 | 60.92 | 60.92 | DEPENDENTE_DO_PDV | 56764 (100.0%) |
| Operador 294273 | 17.83 | 20.94 | DEPENDENTE_DO_PDV | 54193 (100.0%) |
| PDV 54193 | score PDV 26.72 | prejudica? **True** | — | — |
| PDV 15880 | score PDV 44.3 | prejudica? **True** | — | — |

## Ranking ajustado por contexto (top 15)

| Operador | Score bruto | Score ajustado | PDV div. | Turno div. | Classificação |
|----------|-------------|----------------|----------|------------|---------------|
| 276288 | 60.92 | 60.92 | 0.0 | 0.0 | DEPENDENTE_DO_PDV |
| 178278 | 58.16 | 58.16 | 0.0 | 0.0 | DEPENDENTE_DO_PDV |
| 158924 | 43.86 | 43.86 | 0.0 | 0.0 | DEPENDENTE_DO_PDV |
| 227386 | 40.38 | 40.38 | 0.0 | 0.0 | DEPENDENTE_DO_PDV |
| 299371 | 39.39 | 39.39 | 0.0 | 0.0 | INCONCLUSIVO |
| 299151 | 22.8 | 30.32 | 0.0 | 0.0 | INCONCLUSIVO |
| 294273 | 17.83 | 20.94 | 0.0 | 0.0 | DEPENDENTE_DO_PDV |

## Recomendação de ranking

**DUAL_BRUTO_E_AJUSTADO** — performance **MISTA**
