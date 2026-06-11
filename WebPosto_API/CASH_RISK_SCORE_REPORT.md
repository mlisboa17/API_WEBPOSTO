# CASH RISK SCORE REPORT — F03

**Escala:** 0 (risco máximo) → 100 (conformidade perfeita)

## Ponderação obrigatória

| Dimensão | Peso | Implementação |
|----------|------|---------------|
| Operador (W_op) | **40%** | recorrência + severidade por `funcionarioCodigo` |
| PDV (W_pdv) | **25%** | desvio padrão + diff acumulada por terminal |
| Turno (W_tur) | **20%** | volatilidade por `turnoCodigo` |
| Histórico filial (W_hist) | **15%** | média móvel 7d vs 90d |

## Bandas

| Faixa | Classificação |
|-------|---------------|
| 90–100 | Excelente |
| 75–89 | Bom |
| 60–74 | Atenção |
| 0–59 | Crítico |

## Score consolidado rede

| Indicador | Valor |
|-----------|-------|
| **Cash Risk Score** | **53.18** |
| Banda | **Critico** |
| Operadores CRÍTICO | 7 |
| PDVs CRÍTICO | 2 |

## Fórmula

```
Score = 0.40·S_op + 0.25·S_pdv + 0.20·S_turn + 0.15·S_hist
```
