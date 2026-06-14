# IA-2 — Information Architecture

## Mapa final (6 macro áreas)

| Área | Abas de negócio | Motores internos (acessíveis) |
|------|-----------------|--------------------------------|
| Executivo | Resumo, Indicadores, Alertas, Metas | Scorecard, Benchmark, Hub, Copilot, Recommendations, Learning, Decision, Action |
| Financeiro | Receitas…Conciliação (6) | Expenses, Accounts, Finance Center, Cash*, People*, ROI* |
| Combustíveis | Vendas, Tanques, Bombas, LMC, Governança | sales, stock, fuels, lmcIntelligence, fuelGovernance |
| Produtos Vendidos | Vendas, Margem, Mix, Oportunidades, Ações, Resultados | nonFuelProducts, commercialExecution, commercialLearning, commercialCopilot |
| Fiscal | NFCE, Conciliação, Tributação, Riscos | nfce, fiscal, reconciliation |
| Administração | Filiais…Configurações | administration (shell local) |

## Respostas

| Pergunta | Resposta |
|----------|----------|
| Módulos → telas | 6 áreas sidebar |
| Motores → abas | Abas de negócio + faixa "Motores da área" |
| Motores invisíveis | Ocultos da sidebar; acessíveis via abas/faixa |

Config: `frontend/config/navigation.js`
