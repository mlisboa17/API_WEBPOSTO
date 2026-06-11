# FINANCIAL RECOVERY REPORT — F02.1-B

**Fórmula recuperável:** `recuperavel30pct = perdaObservada × 0,30` (benchmark operacional F02.1-A)  
**Projeção anual:** `perdaDiaria × 365`

| Janela | Perda observada (|diff|) | Perda diária | Recuperável 30% | Projeção anual |
|--------|--------------------------|--------------|-----------------|----------------|
| 7d | R$ 1.278,34 | R$ 182,62 | R$ 383,50 | R$ 66.656,30 |
| 30d | R$ 237.959,64 | R$ 7.931,99 | R$ 71.387,89 | R$ 2.895.175,62 |
| 90d | R$ 208.190,40 | R$ 2.313,23 | R$ 62.457,12 | R$ 844.327,73 |

**Potencial anual (90d base):** R$ 844.327,73 observado · R$ 62.457,12 recuperável 30%.

## Limitações

| Janela | Observação |
|--------|------------|
| 365d | Omitida via --skip-365 |
| 30d | `CAIXA_APRESENTADO_REDE` = 0 — projeção 30d usa CAIXA_REDE (1116 reg.) e **superestima** vs. 7d |
| 90d | Base preferida para projeção anual (3000 reg. rede) |
| 7d | Análise causal primária — CAIXA + CAIXA_APRESENTADO (21 fechamentos) |

**Recomendação:** usar **7d** para causa raiz e **90d** para projeção; desconsiderar projeção 30d bruta (R$ 2,89M).
