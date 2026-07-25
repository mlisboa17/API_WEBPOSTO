# Roadmap — webposto CODEX

## Resultado esperado

Entregar à Presidência e à Diretoria uma visão confiável das três empresas licenciadas no WebPosto, com faturamento, custos, despesas, margem e rentabilidade separados por departamento. Nenhum indicador executivo poderá misturar Combustíveis, Conveniência e Lubrificantes.

## Escopo obrigatório

### Empresas licenciadas

| Código | Empresa |
|---:|---|
| 11495 | Posto VIP |
| 5555 | AP Casa Caiada |
| 74014 | Posto Doze Filial II |

### Departamentos gerenciais

| Departamento | Grupos WebPosto confirmados |
|---|---|
| Combustíveis | COMBUSTIVEIS |
| Conveniência | TABACO, BAZAR, DIVERSOS LOJA, FAST FOOD, MERCEARIA, SALGADINHOS-BISCOITOS, SORVETES-GELO, BOMBONIERI e grupos de bebidas |
| Lubrificantes | LUBRIFICANTES, ADITIVOS, FLUIDOS, FILTROS e PALHETAS |

`COMODATO`, `DIVERSOS` e `USO E CONSUMO` permanecem em quarentena e fora dos
KPIs por decisão gerencial de 2026-07-24. Dados sem empresa, grupo ou departamento
devem aparecer como não classificados; nunca serão rateados automaticamente.
O grupo e a classificação cadastrados no WebPosto são preservados como fonte
oficial; o LOGOS acrescenta apenas o estado gerencial de classificação ou quarentena.

## Princípios de produto

1. Verdade antes de aparência: nenhum valor sem origem, período, empresa e departamento.
2. Presidência vê decisão; áreas técnicas veem investigação e evidência.
3. Comparações somente entre bases equivalentes.
4. Ausência de dados deve ser explícita e não pode resultar em zero fictício.
5. Todo KPI precisa permitir rastreamento até o registro de origem do WebPosto.
6. As três empresas são o limite atual de cobertura e autorização.

## Roadmap resumido

| Fase | Objetivo | Sprints | Saída principal |
|---|---|---:|---|
| Fundação | Fixar escopo e verdade dos dados | 0–2 | Cadastro confiável e fatos departamentalizados |
| Inteligência | Calcular indicadores gerenciais | 3–4 | DRE e comparativos por departamento |
| Experiência | Entregar telas por nível decisório | 5–6 | Cockpit da Presidência e painéis da Diretoria |
| Governança | Automatizar controle e operação | 7–8 | Alertas, auditoria, qualidade e rotina executiva |

---

## Sprint 0 — Escopo e governança básica

**Objetivo:** impedir análises fora das três licenças e eliminar consolidações departamentais genéricas.

**Situação:** iniciada e parcialmente entregue.

### Entregas

- Lista autorizada das empresas 11495, 5555 e 74014 no backend e frontend.
- Modelo Pydantic do escopo gerencial.
- Mapa inicial dos 23 grupos retornados por `/INTEGRACAO/GRUPO`.
- Registro dos três grupos ambíguos.
- Dashboard com aviso de cobertura departamental incompleta.
- Documento desta política no contexto do projeto.

### Critérios de aceite

- Nenhuma empresa não licenciada aparece em filtros ou análises.
- Nenhum KPI mistura departamentos sem identificação.
- Testes automatizados validam empresas e mapa de grupos.

---

## Sprint 1 — Inventário e contrato dos dados WebPosto

**Objetivo:** conhecer exatamente quais campos e endpoints sustentam cada indicador.

**Situação:** em andamento. Contratos de catálogo e transacionais, preservação de
`grupoCodigo` e inventário inicial entregues. Pendente validar os contratos contra
amostras reais do Posto Doze e fechar os bloqueios registrados na
`docs/validation/SPRINT_1_ENDPOINT_COVERAGE_MATRIX.md`.

### Entregas

- Inventário dos endpoints por licença: empresas, grupos, produtos, produto-empresa, vendas, itens, estoque, despesas e caixa.
- Dicionário de campos com tipo, obrigatoriedade, exemplo mascarado e qualidade.
- 🔄 Matriz `endpoint × empresa × departamento × período` (duas empresas validadas;
  Posto Doze e cobertura temporal pendentes).
- Definição formal dos tipos `C`, `P` e `U` retornados em `tipoProduto`.
- ✅ Validação gerencial de COMODATO, DIVERSOS e USO E CONSUMO: quarentena.
- ✅ Contratos Pydantic para produto, grupo, venda, item, despesa e caixa.

### Critérios de aceite

- Cada fonte possui proprietário, periodicidade e regra de paginação.
- Cada campo utilizado em KPI tem evidência de origem.
- Respostas incompletas, duplicadas e paginadas são detectadas em testes.

---

## Sprint 2 — Camada de fatos departamentalizados

**Objetivo:** construir uma base única, sem mistura, para cálculos financeiros e operacionais.

### Entregas

- ✅ Dimensões de empresa, departamento, grupo, produto, data e turno no contrato canônico.
- ✅ Classificador por `grupoCodigo`, sem inferência quando falta evidência.
- ✅ Fatos de vendas, custos, despesas, estoque e movimentação de caixa:
  contratos, pipeline diária, persistência privada e API de qualidade entregues.
- ✅ Quarentena para registros sem empresa ou departamento.
- ✅ Deduplicação e reconciliação no lote canônico.
- ✅ Linhagem completa: token lógico, endpoint, empresa, período e horário da coleta.

### Critérios de aceite

- 100% dos registros classificados ou explicitamente colocados em quarentena.
- Soma por departamento reconcilia com a origem dentro da tolerância aprovada.
- Nenhum fato autorizado contém empresa fora das três licenças.

---

## Sprint 3 — KPIs e DRE por departamento

**Objetivo:** calcular rentabilidade real e comparável para cada operação.

### Entregas

- 🔄 Faturamento, CMV e margem bruta por empresa e departamento entregues;
  despesas, resultado e rentabilidade bloqueados até cobertura completa.
- 🔄 Indicadores específicos de Combustíveis: litros, preço médio, custo e margem
  por litro entregues; perdas pendentes.
- 🔄 Indicadores de Conveniência: ticket, itens por venda e margem entregues;
  giro, ruptura e perdas pendentes.
- 🔄 Indicadores de Lubrificantes: volume e margem unitária entregues;
  margem por produto, giro, estoque parado e venda cruzada pendentes.
- Tratamento explícito de despesas compartilhadas, sem rateio até aprovação da regra.
- API versionada de KPIs departamentais.

### Critérios de aceite

- Todo KPI retorna valor, unidade, empresa, departamento, período e linhagem.
- Valores sem custo ou despesa identificada não são apresentados como lucro.
- Cálculos possuem testes unitários com casos positivos, negativos e ausentes.

---

## Sprint 4 — Comparativos, metas e oportunidades

**Objetivo:** transformar os indicadores em leitura gerencial acionável.

### Entregas

- ✅ Comparação entre as três empresas dentro do mesmo departamento.
- ✅ Comparação temporal para qualquer intervalo (dia, semana ou mês) contra o
  período anterior de igual duração, publicada apenas com todos os dias presentes.
- 🔄 Metas independentes por empresa e departamento: contrato preparado para a
  próxima rodada; valores aguardam aprovação gerencial e não serão inventados.
- 🔄 Ranking de margem bruta entregue; lucro, crescimento e eficiência dependem
  de despesas classificadas e histórico comparável.
- Identificação de anomalias e oportunidades com impacto financeiro estimado.
- 🔄 Recomendações conservadoras de cobertura entregues; oportunidades financeiras
  aguardam histórico equivalente e metas aprovadas.

### Critérios de aceite

- Nenhum ranking compara métricas de departamentos diferentes.
- Toda recomendação informa evidência, impacto, responsável sugerido e prazo.
- Comparações sinalizam baixa cobertura ou bases não equivalentes.

---

## Sprint 5 — Cockpit da Presidência

**Objetivo:** permitir compreender a situação do Grupo e decidir em menos de 60 segundos.

### Entregas

- ✅ Primeira dobra com situação geral e cobertura dos dados.
- ✅ Três blocos independentes: Combustíveis, Conveniência e Lubrificantes.
- Para cada departamento: lucro, margem, tendência, melhor empresa, pior empresa e principal risco.
- ✅ Lista curta de decisões prioritárias; impacto em reais fica nulo quando não
  houver base reproduzível.
- ✅ Navegação por exceção: resumo → departamento → evidência.
- ✅ Linguagem executiva, sem termos técnicos desnecessários.

### Critérios de aceite

- Teste com usuário: identificar o principal risco e a melhor oportunidade em até 60 segundos.
- Nenhum card mostra consolidação genérica.
- Toda decisão abre sua evidência detalhada.

---

## Sprint 6 — Painéis da Diretoria

**Objetivo:** oferecer investigação e acompanhamento por responsabilidade.

### Entregas

- 🔄 Painel Financeiro: DRE e cobertura por departamento entregues; caixa, despesas
  e conciliação aguardam classificação departamental completa.
- 🔄 Painel Comercial: margem, ticket e comparação temporal entregues; metas e
  oportunidades aguardam histórico/metas aprovadas.
- 🔄 Painel Operacional publicado com limitações explícitas; perdas, rupturas,
  LMC e produtividade ainda não têm fatos departamentais equivalentes.
- ✅ Filtros consistentes de empresa e período; departamentos permanecem separados.
- ✅ Contrato de exportação preserva empresa, departamento, período e linhagem.

### Critérios de aceite

- Presidência e Diretoria veem o mesmo número na mesma combinação de filtros.
- Cada painel possui responsável e ação operacional correspondente.
- Exportações preservam empresa e departamento em todas as linhas.

---

## Sprint 7 — Alertas e auditoria contínua

**Objetivo:** detectar vazamentos e desvios antes do fechamento gerencial.

### Entregas

- 🔄 Alertas reproduzíveis de cobertura, despesas não classificadas e margem bruta
  negativa entregues; caixa, estoque e faturamento aguardam fatos equivalentes.
- 🔄 Regras separadas por departamento; limiares financeiros adicionais aguardam
  aprovação gerencial.
- ✅ Detecção da ausência de classificação departamental das despesas.
- ✅ Fluxo de reconhecimento, responsável, prazo, justificativa e encerramento.
- ✅ Histórico atômico de alterações e evidências em área privada.

### Critérios de aceite

- Alertas possuem severidade, impacto estimado e regra reproduzível.
- Nenhum alerta é criado a partir de dado sem cobertura mínima.
- Encerramento exige evidência ou justificativa registrada.

---

## Sprint 8 — Operação, segurança e evolução

**Objetivo:** tornar o produto confiável para uso diário da alta gestão.

### Entregas

- 🔄 Monitoramento de disponibilidade e qualidade por empresa entregue; telemetria
  histórica de latência e paginação permanece pendente.
- ✅ Respostas de saúde nunca retornam valores das três credenciais.
- ✅ Perfis de Presidência, Diretoria, Auditoria e Operação definidos.
- 🔄 Política de retenção e recuperação documentada; exclusão automática e teste
  de restauração permanecem desabilitados até validação operacional.
- 🔄 Relatório diário entregue por API; configuração governada permite alterar as
  rotinas diária e semanal. O padrão diário aprovado é 06:00
  (`America/Sao_Paulo`), processando os lançamentos do dia anterior. Ativação do
  executor do agendamento permanece pendente.
- ✅ Runbook formaliza os controles para novas materializações e escalonamento.

### Critérios de aceite

- Falhas de API ou dados aparecem antes de afetar decisões.
- Segredos não aparecem em logs, telas ou repositório.
- Inclusão de empresa exige licença, cadastro, teste de contrato e aprovação.

## Backlog prioritário

### Sprint 21 — Experiência móvel e acessibilidade operacional

- ✅ Navegação departamental rolável em telas estreitas.
- ✅ Controles com área mínima adequada para toque.
- ✅ Tabelas responsivas sem estouro horizontal da página.
- ✅ Validação departamental em viewport móvel de 390 × 844.

### Sprint 22 — Regressão automática das telas

- ✅ Matriz executável das 41 rotas do cockpit e da tela departamental.
- ✅ Verificação de renderização, respostas HTTP e estado responsivo.
- ✅ Evidência JSON reutilizável em CI e nas revisões de sprint.

### Sprint 23 — Desempenho departamental

- ✅ Linha de base dos endpoints do painel departamental.
- ✅ Cache de leitura dos fatos, invalidado por versão física do arquivo.
- ✅ Mediana aquecida do relatório diário reduzida de 654 ms para menos de 60 ms.

### Sprint 24 — Orçamento contínuo de desempenho

- ✅ Validador reproduzível do relatório departamental.
- ✅ Limite inicial de 150 ms para a mediana aquecida.
- ✅ Evidência JSON pronta para integração contínua.

### Sprint 25 — Persistência concorrente segura

- ✅ Trava entre processos para metas, alertas e auditorias em JSON.
- ✅ Gravação atômica preservada e locks abandonados recuperáveis.
- ✅ Teste concorrente contra perda de atualização.

### Sprint 26 — Consultas sem efeitos colaterais

- ✅ GET de alertas e relatório diário operam somente em leitura.
- ✅ Avaliação de alertas movida para POST autenticado.
- ✅ Automação diária atualizada para avaliar antes de consultar.

### Sprint 27 — Homologação e segurança de produção

- ✅ Inicialização de produção bloqueia segredos e senhas padrão.
- ✅ Cookies seguros e CORS explícito configuráveis por ambiente.
- ✅ Perfil de autorização preservado após renovação do token.
- ✅ Modelo de ambiente e runbook atualizados.

### Sprint 28 — Configuração governada das rotinas

- ✅ Rotinas diária e semanal configuráveis pelo usuário.
- ✅ Horário, fuso, ativação, defasagem diária, dia semanal e janela validados.
- ✅ Alterações protegidas por perfil autorizado e com autoria registrada.
- ✅ Configuração disponível na aba Auditorias e persistida de forma atômica.
- 🔄 Acionador operacional automático ainda precisa ser ativado no ambiente de
  produção.

### Sprint 29 — Executor idempotente e histórico operacional

- ✅ Executor identifica rotinas vencidas conforme fuso e configuração vigentes.
- ✅ Rotina diária materializa as três empresas e avalia alertas do período.
- ✅ Fechamento semanal respeita o dia e a janela definidos pelo usuário.
- ✅ Trava entre processos impede execução duplicada da mesma janela.
- ✅ Sucessos e falhas ficam registrados em histórico consultável.
- 🔄 Disparo periódico do executor ainda depende da ativação no ambiente de
  produção.

### Sprint 30 — Operação automática e monitoramento

- ✅ Disparador interno consulta rotinas vencidas em intervalo configurável.
- ✅ Ativação operacional controlada por variável de ambiente.
- ✅ Alterações feitas pelo usuário são lidas sem recriar o agendamento.
- ✅ Execuções travadas há mais de uma hora podem ser recuperadas.
- ✅ Tarefa em segundo plano é cancelada com segurança no desligamento.
- ✅ Histórico de sucesso e falha aparece na aba Auditorias.
- ⚙️ Produção deve definir `DEPARTMENTAL_SCHEDULER_ENABLED=true`.

### Sprint 31 — Evidência PDF governada

- ✅ Upload autenticado de PDF vinculado à execução da auditoria.
- ✅ Validação de assinatura, estrutura, criptografia, tamanho e páginas.
- ✅ Armazenamento privado, nome sanitizado e integridade SHA-256.
- ✅ Reenvio do mesmo documento é idempotente.
- ✅ Metadados podem ser consultados sem expor o caminho físico do arquivo.
- 🔄 Extração dos totais e conciliação PDF × API continuam na próxima etapa.

### Sprint 32 — Extração e conciliação PDF × API

- ✅ Layout real de seis páginas inspecionado visualmente.
- ✅ Período, apresentado, sangria, apurado e diferença extraídos do PDF real.
- ✅ Valores brasileiros são normalizados com precisão decimal.
- ✅ Sangria é comparada com o fato equivalente disponível na API.
- ✅ Campos sem equivalente na API ficam explicitamente indisponíveis.
- ✅ Nenhum resultado permite aprovação automática; revisão humana permanece
  obrigatória.
- 🔄 A interface de upload e visualização da conciliação será concluída na próxima
  sprint.

### Sprint 33 — Interface de evidência e divergências

- ✅ Execuções abertas são carregadas no painel executivo.
- ✅ Diretor pode selecionar e enviar o PDF diretamente na execução.
- ✅ Proxy preserva autenticação e transmite o arquivo como `application/pdf`.
- ✅ Conciliação é iniciada após a validação do documento.
- ✅ Resultado apresenta PDF, API e estado de cada métrica.
- ✅ Interface reforça que a revisão humana permanece obrigatória.

### Sprint 34 — Trilha documental e aprovação governada

- ✅ Resultado da conciliação é persistido dentro da execução.
- ✅ Hash, métricas, autor e horário ficam registrados.
- ✅ Reprocessar a mesma evidência substitui o resultado anterior sem duplicação.
- ✅ Conciliação e revisão humana geram eventos na trilha de auditoria.
- ✅ Diretor/Auditor registra justificativa explícita na interface.
- ✅ Aprovação fica bloqueada enquanto existir conciliação sem revisão humana.
- ✅ Execuções legadas continuam compatíveis com o novo contrato.

### Sprint 35 — Dossiê final da auditoria

- ✅ Dossiê PDF disponível somente após aprovação da execução.
- ✅ Documento contém escopo, checklist, evidências e conciliações.
- ✅ Hashes, revisões, justificativas e trilha de eventos são preservados.
- ✅ Exportação autenticada usa cache privado e não expõe arquivos internos.
- ✅ Download está disponível no painel para execuções aprovadas.
- ✅ Estrutura, extração textual e renderização visual foram validadas.

### Sprint 36 — Arquivo imutável e integridade do dossiê

- ✅ Primeira emissão aprovada é arquivada de forma imutável.
- ✅ Manifesto preserva SHA-256, tamanho, emissão e aprovação.
- ✅ Downloads posteriores validam o arquivo antes da entrega.
- ✅ Trava entre processos torna a geração concorrente idempotente.
- ✅ Adulteração e arquivo incompleto são detectados e bloqueados.
- ✅ API autenticada e painel permitem verificar a integridade.

### Sprint 37 — Retenção, backup e restauração

- ✅ Retenção configurável com padrão de sete anos e mínimo de um ano.
- ✅ Exclusão automática permanece desabilitada.
- ✅ Backup idempotente preserva PDF, manifesto e SHA-256.
- ✅ Volume de backup pode ser separado por configuração de ambiente.
- ✅ Criação, reutilização e restauração registram autor e horário.
- ✅ Restauração valida a integridade antes e depois da cópia.
- ✅ Backup adulterado e sobrescrita insegura são bloqueados.
- ✅ APIs de backup, verificação e restauração são protegidas por perfil.
- ✅ Runbook operacional e teste controlado de restauração foram concluídos.

### Sprint 38 — Fundação da Inteligência Executiva Proativa

- ✅ Visão de Conselheiro Executivo adaptada ao domínio real do WebPosto.
- ✅ Radar Executivo Diário gerado automaticamente após a rotina das 06:00.
- ✅ Mudanças de cobertura das últimas 24 horas são destacadas.
- ✅ Riscos são priorizados pelos pesos financeiro, estratégico, tempo e risco.
- ✅ Cada insight preserva evidência, confiança, responsável e ação recomendada.
- ✅ Perguntas sem dados equivalentes retornam bloqueio explícito.
- ✅ Clientes, contratos, churn e projetos permanecem fora do escopo até homologação.
- ✅ Radar persistido pode ser consultado por data ou pela última execução.

### Sprint 39 — Notificações e valor gerado pela inteligência

- ✅ Prioridades geram notificações idempotentes para Presidência e Diretoria.
- ✅ Toda notificação contém evidência, confiança, impacto, responsável, ação e prazo.
- ✅ Caixa de saída interna preserva histórico e estado da entrega.
- ✅ Webhook HTTPS opcional permite entrega ativa fora do painel.
- ✅ Recomendações percorrem aceitação, execução e confirmação com evidência.
- ✅ Potencial identificado permanece separado de valor financeiro confirmado.
- ✅ Receita, custos evitados, riscos mitigados e horas poupadas são mensurados.
- ✅ Executive Value Score consolida valor confirmado, velocidade e adoção.
- ✅ APIs protegidas e painel da Presidência expõem o acompanhamento.
- ✅ Arquitetura futura prevê agentes Financeiro, Operacional, Comercial,
  Governança e Presidência sob as mesmas regras de evidência.

### Sprint 40 — Agentes proativos especializados

- ✅ Agentes Financeiro, Operacional, Comercial e Governança possuem escopos separados.
- ✅ Todos exigem fonte, evidência, justificativa, confiança e linhagem.
- ✅ Ausência de evidência retorna a mensagem explícita de insuficiência.
- ✅ Agente da Presidência coordena e deduplica as recomendações especializadas.
- ✅ Contribuição de cada agente permanece visível na prioridade consolidada.
- ✅ Coordenador não cria fatos, não aumenta confiança e não executa ações.
- ✅ Parecer diário é persistido e integrado à rotina automática.
- ✅ API protegida e painel da Presidência exibem o conselho de agentes.

### Sprint 41 — Aprendizado baseado em valor real

- ✅ Ciclo completo: gerada, entregue, visualizada, aceita/rejeitada, implementada e validada.
- ✅ Aprendizado e EVS usam somente resultados validados com evidência.
- ✅ Validação financeira exige perfil independente de Auditoria, Administração ou Proprietário.
- ✅ Potencial estimado permanece separado do Business Value Generated by AI.
- ✅ Métricas individuais cobrem adoção, implementação, falsos positivos e valor.
- ✅ Agent Reliability Score usa apenas precisão e resultados historicamente observados.
- ✅ Agentes sem amostra factual permanecem sem score de confiabilidade.
- ✅ Valor compartilhado é dividido entre agentes para impedir dupla contagem.
- ✅ Presidência visualiza valor mensal, adoção, agente líder e resultados de maior impacto.
- ✅ Registros legados de execução e confirmação permanecem reconhecidos.

### Sprint 42 — Executive Experience e adoção pela alta gestão

- ✅ Entrada da Presidência reduzida a quatro blocos de decisão.
- ✅ Análises detalhadas permanecem disponíveis em um único clique.
- ✅ shadcn/ui é o padrão de composição e Recharts apresenta valor da IA.
- ✅ Valor comprovado e estimado permanecem visualmente separados.
- ✅ Riscos e oportunidades sem evidência exibem bloqueio explícito.
- ✅ Tema claro/escuro, fontes maiores e botões de toque amplo foram preservados.
- ✅ Layout responde a tablets, notebooks e telas estreitas.
- ✅ Telemetria mede tempo, cliques, uso e funcionalidades ignoradas.
- ✅ Telemetria não armazena valores, evidências ou conteúdo executivo.
- ✅ APIs de inteligência e adoção permanecem protegidas por autenticação.

### Sprint 43 — Validação executiva e melhoria orientada por uso

- ✅ Protocolo de 30 segundos para teste com Presidente/Diretor.
- ✅ Métricas de adoção com meta ≤ 30s por bloco.
- ✅ Revisão dos quatro blocos da Presidência conforme engajamento observado.
- ✅ Relatório mensal Business Value Generated by AI com separação validado/estimado.
- ✅ Homologação de webhook externo sem expor dados de negócio.
- ✅ Smoke operacional e testes de integração da sprint.

### Sprint 44 — Preparação da Sessão Executiva 30s

- ✅ Validação de integridade de paginação com alertas de perda de dados.
- ✅ Tratativa de despesas pendentes sem quebrar pipeline da DRE.
- ✅ Centro de custo "PENDENTE_CLASSIFICACAO" com alerta visual.
- ✅ Síntese executiva consolidada com cache < 1s.
- ✅ Endpoints de Dashboard sintético para visão do Presidente.
- ✅ Migração FastAPI `on_event` → `lifespan` (elimina deprecation warnings).

### Sprint 45 — Regras de Negócio e Sanidade Financeira

- ✅ Enum de classificação de despesas configurável por plano de contas.
- ✅ Mecanismo de rateio dinâmico (%, faturamento ou valor fixo).
- ✅ Enum de tipos de produto C/P/U com fallback seguro.
- ✅ Testes unitários: paginação, despesas pendentes, rateio.
- 🔄 Classificar 23 despesas pendentes via interface.
- 🔄 Aprovar regras de rateio com Diretoria.

### Sprint 20 — Auditoria periódica de prestação de contas

Automatizar a conferência semanal ou a cada X dias do relatório **Prestação de
Contas** do WebPosto. O sistema deverá criar ciclos de auditoria por empresa,
conferir caixa, dinheiro, sangrias, despesas, vales, cartões, transferências,
movimento bancário e vendas; abrir revisão humana apenas para exceções. O PDF
exportado poderá ser anexado como evidência, mas os fatos WebPosto continuam sendo a
fonte de cálculo. Ver `SPRINT_20_PRESTACAO_DE_CONTAS_AUDITORIA.md`.

### P0 — bloqueia confiança

- Confirmar significado dos tipos de produto `C`, `P` e `U`.
- ✅ Manter COMODATO, DIVERSOS e USO E CONSUMO em quarentena.
- Recuperar `grupoCodigo` no catálogo normalizado.
- Garantir paginação integral de produtos, vendas e despesas.
- Definir regra para custos e despesas compartilhadas.

### P1 — gera valor executivo

- DRE por empresa e departamento.
- Margem por litro e perdas de Combustíveis.
- Margem, ticket e ruptura de Conveniência.
- Giro e estoque parado de Lubrificantes.
- Comparativos e metas por departamento.

### P2 — escala e automação

- Alertas automáticos.
- Relatórios recorrentes.
- Fluxo de responsabilização.
- Exportação executiva e trilha de auditoria.

## Indicadores de sucesso do projeto

| Indicador | Meta |
|---|---:|
| Empresas fora do escopo em análises | 0 |
| KPIs com empresa, departamento e linhagem | 100% |
| Registros não classificados | < 2%, sempre visíveis |
| Reconciliação com WebPosto | ≥ 99,5% ou tolerância aprovada |
| Tempo para identificar principal risco | ≤ 60 segundos |
| Alertas sem evidência | 0 |
| Segredos expostos | 0 |

## Próximo marco

✅ Histórico real de 17 a 23/07/2026 materializado nas três empresas. As rotinas
diária e semanal agora possuem configuração governada; o padrão diário é 06:00
(`America/Sao_Paulo`) sobre o dia anterior. Próximos passos: ativar o executor e
aprovar metas; Casa Caiada em 19/07 permanece como base não equivalente para
investigação.
