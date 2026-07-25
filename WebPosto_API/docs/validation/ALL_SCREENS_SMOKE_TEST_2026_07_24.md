# Teste de fumaça de todas as telas

Data: 24/07/2026  
Ambiente: `http://127.0.0.1:8040`  
Período usado: 17/07/2026 a 23/07/2026

## Resultado

- 42 telas/rotas verificadas no navegador.
- 42 telas renderizaram uma área ativa ou um título identificável.
- A tela Gestão Departamental renderizou com seus controles.
- Não houve erro de console da aplicação no último lote.
- A tentativa de percorrer todas as telas em uma única sessão excedeu 120
  segundos. Dividida em quatro lotes, a verificação foi concluída.

Este é um teste de fumaça de carregamento e roteamento. Ele não substitui testes
funcionais de cada botão, formulário e fluxo autenticado.

## Rotas verificadas

### Financeiro, operação e pessoas

- Centro Financeiro
- Fluxo de Caixa
- Operações de Caixa
- Performance de Operadores
- People Intelligence
- People ROI
- Operation ROI
- Gestão de Ações
- Metas e Campanhas
- Benchmark

### Executivo e governança

- Indicadores Executivos
- Hub Corporativo
- Motor de Decisão
- Central de Alertas
- Conferência Financeira
- Visão da Rede
- Acompanhamento Executivo
- Detalhe do Acompanhamento
- Detalhe da Decisão
- Copiloto Executivo
- Recomendações
- Aprendizado
- Painel do Presidente
- Workspace Executivo

### Fiscal, combustível e comercial

- Inteligência NFCE
- Inteligência LMC
- Inteligência Fiscal
- Conciliação Fiscal
- Governança de Combustíveis
- Produtos Não Combustíveis
- Execução Comercial
- Aprendizado Comercial
- Copiloto Comercial
- Produtos Vendidos

### Administração e finanças avançadas

- Administração
- Centro de Operações Financeiras
- Inteligência Financeira
- Visão Financeira
- Caixa de Conferências
- Detalhe da Conferência
- Tesouraria

### Departamental

- Gestão Departamental

## Comportamentos esperados confirmados

Algumas rotas são aliases ou abas de um mesmo hub:

- Centro Financeiro e Fluxo de Caixa abrem o hub de Tesouraria.
- People ROI e Operation ROI abrem Administração.
- Metas e Benchmark abrem Indicadores.
- Gestão de Ações, Motor de Decisão, Recomendações e Aprendizado abrem Alertas.
- Produtos Não Combustíveis e as rotas comerciais abrem o hub de Produtos.

## Próximos testes recomendados

1. Validar ações e formulários com usuário autenticado.
2. Testar os estados de detalhe usando IDs reais.
3. Repetir as telas prioritárias em resolução móvel.
4. Medir APIs lentas por tela e reduzir o tempo total da varredura.
5. Automatizar esta matriz para execução contínua.

