# IA-4 — Alert Center Report (UX-02)

## Painel centralizado (Bloco 2)

### Classificação de severidade

| Nível | Uso |
|-------|-----|
| CRÍTICO | Risco imediato à operação/fiscal |
| ALTO | LMC atrasado, dias sem LMC |
| MÉDIO | Mix abaixo meta, NFCE, evidências |
| BAIXO | Reservado para expansão |

### Origens mapeadas

| Origem | Gatilhos |
|--------|----------|
| Combustível | LMC atrasado, dias sem LMC |
| Fiscal | Riscos NFCE (`nfceRiskEngine`) |
| Financeiro | Ações sem evidência (`actionCenter`) |
| Comercial | Mix abaixo da meta (`nonFuelProducts`) |

## Comportamento UX

- Ordenação por `severityRank` (crítico primeiro).
- Máximo 8 alertas visíveis na home.
- Clique navega para view de origem (`data-nav-view`).

## Arquivo

`frontend/services/workspaceEngine.js` — array `alerts`.

## Parecer IA-4

Alert Center operacional, classificado e com origem rastreável — sem alterar motores backend.
