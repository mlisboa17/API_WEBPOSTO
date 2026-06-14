# IA-3 — Executive Cards Report (UX-02)

## Camada de indicadores (Bloco 1)

| Card | Fonte de dados | Hint |
|------|----------------|------|
| Receita | `executiveScorecard` / Produtos Vendidos | Rede consolidada |
| Margem | `commercialExecution` / Produtos Vendidos | PV + execução |
| Combustível | `fuelGovernance` LMC | Conformidade operacional |
| Produtos Vendidos | `nonFuelProducts` | Receita não combustível |
| NFCE | `nfceIntelligence` | Conciliação fiscal |
| Filiais Ativas | `filiais.js` registry Onda 1 | Contagem ativa |

## Cards derivados (outros blocos)

| Domínio | Bloco | Métricas |
|---------|-------|----------|
| Mix | Branch Intelligence | `mixPorFilial` |
| ROI | Execução | receita realizada / taxa execução |
| Governança | Alert Center | LMC, NFCE, evidências |
| Execução | Bloco 4 | abertas / executadas / validadas |
| Filiais | Bloco 5 | top, risco, LMC, mix, dependência |

## Implementação

```javascript
// workspaceEngine.js — buildExecutiveWorkspace()
summary: [ receita, margem, combustivel, produtos, nfce, filiais ]
```

## Parecer IA-3

Camada de executive cards implementada com fallback entre cockpits existentes (snapshot-first).
