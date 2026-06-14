# IA-4 — Tabs Migration

## Padrão

- Abas renderizadas dinamicamente por área (`#areaTabs`)
- Cada aba mapeia `data-view` → motor existente (sem nova rota API)
- Deep links preservados via `?view=` existente

## Exemplo Produtos Vendidos

| Aba | View interna |
|-----|--------------|
| Vendas | nonFuelProducts |
| Margem | nonFuelProducts |
| Mix | nonFuelProducts |
| Oportunidades | commercialCopilot |
| Ações | commercialExecution |
| Resultados | commercialLearning |

Motores comerciais **não** aparecem como botões de topo.
