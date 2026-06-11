# PRESTAÇÃO GAP ANALYSIS — D02 · Agente 8

Cobertura D01: **87.5%** → D02: **97.5%**

| Campo | Origem | Na API? | Calculável? | Inferível? |
|---|---|---|---|---|
| funcionarioNome | /INTEGRACAO/FUNCIONARIO.nome | **Sim** | **Não** | **Não** |
| participacaoIndividual | calculavel_venda | **Não** | **Sim** | **Sim** |
| produtividadeFuncionario | proxy_venda_abastecimento | **Não** | **Sim** | **Sim** |
| metaFuncionario | grupo_meta_isolado | **Não** | **Não** | **Não** |
| fundoCaixa | caixa_abertura_parcial | **Sim** | **Sim** | **Sim** |
| layoutOperacionalTurno | prestacao_pdf | **Não** | **Não** | **Não** |

## Respostas

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | O que continua exclusivo? | metaFuncionario, layoutOperacionalTurno |
| 2 | O que pode ser calculado? | participacaoIndividual, produtividadeFuncionario, fundoCaixa |
| 3 | O que pode ser inferido? | participacaoIndividual, produtividadeFuncionario, fundoCaixa |
| 4 | O que não existe na API? | metaFuncionario, layoutOperacionalTurno |
