# IA-6 — Branch Intelligence Report (UX-02)

## Visão por filial (Bloco 5)

| Ranking | Critério | Fonte |
|---------|----------|-------|
| Top filiais | Receita / score / conformidade | `commercialPerformance.porFilial` ou ranking LMC |
| Filiais em risco | Menor score/conformidade | Mesma base, sort invertido |
| Sem LMC | Atrasos LMC | `fuelGovernance.delayAnalysisEngine` |
| Melhor mix | Maior mix PV % | `nonFuelProducts.mixPorFilial` |
| Dependência combustível | Maior % dependência | `dependenciaCombustivel` / `fuelRiskEngine` |

## Formato

Lista compacta: filial · métrica · tag (Destaque/Risco/LMC/Mix/Dependência).

Top 5 por categoria.

## Parecer IA-6

Branch Intelligence com 5 rankings decisórios — filial como unidade de ação.
