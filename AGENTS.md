## Imported Claude Cowork project instructions

## 9. Otimizacao de tokens e versionamento

- Otimizar o uso de tokens em respostas, implementacoes e processamento de dados.
- Evitar redundancias, loops desnecessarios, arquivos duplicados e codigo excessivo.
- Priorizar solucoes enxutas, performaticas e faceis de manter.
- Reutilizar funcoes, componentes e estruturas existentes sempre que possivel.
- Usar Git como parte do fluxo de trabalho quando houver alteracoes relevantes.
- Fazer commits frequentes, organizados e com mensagens claras quando solicitado ou quando o escopo estiver pronto.
- Manter o historico limpo e adequado para colaboracao futura.
- Preparar o projeto para GitHub com README claro, estrutura de pastas coerente e documentacao basica.
- Nao versionar segredos, tokens, arquivos `.env` reais ou dados sensiveis.

Logos Mode: ON. >

Atue como meu Engenheiro de Software Sênior e Especialista em Auditoria de Postos. Usando sua habilidade de Artifacts, crie uma tela de Dashboard em React/Tailwind para o sistema Logos Auditoria.



Objetivo: Conferir se as informações de fechamento de caixa do webPosto são verídicas e identificar vazamentos.



A tela deve conter:



Header com Seletor de Unidade: (Real, Casa Caiada, VIP) e Filtro de Data.



Cards de Resumo (KPIs):



Faturamento Bruto: Total vendido.



Despesas de Caixa (Aba Despesas): Total gasto na pista/conveniência.



Quebra de Caixa: Diferença entre o esperado e o informado pelo operador.



Tabela de Auditoria de Despesas: >    - Colunas: [Horário, Categoria (Luz, Gelo, Vales, etc.), Valor, Operador, Status de Justificativa].



Marque em vermelho despesas sem categoria ou sem anexo de documento.



Habilidade de Verificação Estoica: Adicione um painel lateral chamado "Insights do Auditor" que aponte inconsistências gritantes (ex: "A unidade VIP teve 30% a mais de despesas de caixa que a média das outras").



Configuração Técnica: > - Simule dados de exemplo baseados na estrutura JSON da API webPosto que discutimos.



O código deve ser modular e usar Pydantic para a lógica de validação de dados interna.



Estilo visual: Dark Mode, pragmático, focado em dados e sem distrações visuais.



Saída: Apenas o Artifact funcional. Sem explicações longas. Vá direto ao ponto.







Logos Mode: ON.



Como meu Engenheiro Sênior, atualize o Dashboard de Auditoria usando Artifacts. O objetivo agora é consolidar todos os valores dos caixas (Pista, Conveniência e Restaurante) extraídos via API do webPosto.



Novas Funcionalidades Mandatórias:



Visão Geral Financeira (Cards):



Faturamento Total: Soma de todas as vendas brutas.



Despesas Operacionais: Total extraído da "Aba Despesas" de todos os caixas.



Saldo em Espécie: Total em dinheiro que deve estar fisicamente nos cofres/caixas.



Tabela de Movimentação por Espécie:



Crie uma tabela que detalhe os valores por modalidade: [Dinheiro, PIX, Cartão Débito, Cartão Crédito, Frotistas/Prazo].



Adicione uma coluna para "Diferença" (Valor Sistêmico vs. Valor Informado pelo Operador).



Módulo de Fechamento de Turno:



Liste todos os caixas abertos e fechados no dia.



Destaque em laranja caixas que ainda não foram consolidados.



Destaque em vermelho qualquer caixa com quebra financeira acima de R$ 10,00.



Habilidade de Auditoria Estoica:



O painel lateral de insights deve agora comparar o faturamento entre as unidades (Real, Casa Caiada, VIP) e alertar se a proporção de "Despesas de Caixa" estiver fora do padrão histórico de 5%.



Saída: Gere o código React/Tailwind funcional. Priorize a clareza dos dados e a velocidade de leitura para conferência rápida no Coworking.,
