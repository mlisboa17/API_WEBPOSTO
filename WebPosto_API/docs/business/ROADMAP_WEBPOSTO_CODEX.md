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

`COMODATO`, `DIVERSOS` e `USO E CONSUMO` permanecem fora dos KPIs até validação gerencial. Dados sem empresa, grupo ou departamento devem aparecer como não classificados; nunca serão rateados automaticamente.

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

**Situação:** em andamento. Contrato de catálogo, preservação de `grupoCodigo` e inventário inicial entregues; contratos transacionais permanecem pendentes.

### Entregas

- Inventário dos endpoints por licença: empresas, grupos, produtos, produto-empresa, vendas, itens, estoque, despesas e caixa.
- Dicionário de campos com tipo, obrigatoriedade, exemplo mascarado e qualidade.
- Matriz `endpoint × empresa × departamento × período`.
- Definição formal dos tipos `C`, `P` e `U` retornados em `tipoProduto`.
- Validação gerencial de COMODATO, DIVERSOS e USO E CONSUMO.
- Contratos Pydantic para produto, grupo, venda, item, despesa e caixa.

### Critérios de aceite

- Cada fonte possui proprietário, periodicidade e regra de paginação.
- Cada campo utilizado em KPI tem evidência de origem.
- Respostas incompletas, duplicadas e paginadas são detectadas em testes.

---

## Sprint 2 — Camada de fatos departamentalizados

**Objetivo:** construir uma base única, sem mistura, para cálculos financeiros e operacionais.

### Entregas

- Dimensões de empresa, departamento, grupo, produto, data e turno.
- Classificador por `grupoCodigo`, com fallback controlado por evidência.
- Fatos de vendas, custos, despesas, estoque e movimentação de caixa.
- Quarentena para registros sem empresa ou departamento.
- Deduplicação e reconciliação de paginação.
- Linhagem completa: token lógico, endpoint, empresa, período e horário da coleta.

### Critérios de aceite

- 100% dos registros classificados ou explicitamente colocados em quarentena.
- Soma por departamento reconcilia com a origem dentro da tolerância aprovada.
- Nenhum fato autorizado contém empresa fora das três licenças.

---

## Sprint 3 — KPIs e DRE por departamento

**Objetivo:** calcular rentabilidade real e comparável para cada operação.

### Entregas

- Faturamento, CMV, margem bruta, despesas, resultado e rentabilidade por empresa e departamento.
- Indicadores específicos de Combustíveis: litros, preço médio, custo, margem por litro e perdas.
- Indicadores de Conveniência: ticket, itens por venda, margem, giro, ruptura e perdas.
- Indicadores de Lubrificantes: volume, margem por produto, giro, estoque parado e venda cruzada.
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

- Comparação entre as três empresas dentro do mesmo departamento.
- Comparação temporal: dia, semana, mês e mesmo período anterior.
- Metas independentes por empresa e departamento.
- Ranking de lucro, margem, crescimento e eficiência.
- Identificação de anomalias e oportunidades com impacto financeiro estimado.
- Regras de recomendação específicas por departamento.

### Critérios de aceite

- Nenhum ranking compara métricas de departamentos diferentes.
- Toda recomendação informa evidência, impacto, responsável sugerido e prazo.
- Comparações sinalizam baixa cobertura ou bases não equivalentes.

---

## Sprint 5 — Cockpit da Presidência

**Objetivo:** permitir compreender a situação do Grupo e decidir em menos de 60 segundos.

### Entregas

- Primeira dobra com situação geral e cobertura dos dados.
- Três blocos independentes: Combustíveis, Conveniência e Lubrificantes.
- Para cada departamento: lucro, margem, tendência, melhor empresa, pior empresa e principal risco.
- Lista curta de decisões prioritárias com impacto em reais.
- Navegação por exceção: resumo → empresa → departamento → evidência.
- Linguagem executiva, sem termos técnicos desnecessários.

### Critérios de aceite

- Teste com usuário: identificar o principal risco e a melhor oportunidade em até 60 segundos.
- Nenhum card mostra consolidação genérica.
- Toda decisão abre sua evidência detalhada.

---

## Sprint 6 — Painéis da Diretoria

**Objetivo:** oferecer investigação e acompanhamento por responsabilidade.

### Entregas

- Painel Financeiro: DRE, caixa, despesas e conciliação por departamento.
- Painel Comercial: mix, margem, ticket, metas e oportunidades.
- Painel Operacional: estoque, perdas, rupturas, LMC e produtividade.
- Filtros consistentes de empresa, departamento e período.
- Exportação de relatórios com escopo e linhagem visíveis.

### Critérios de aceite

- Presidência e Diretoria veem o mesmo número na mesma combinação de filtros.
- Cada painel possui responsável e ação operacional correspondente.
- Exportações preservam empresa e departamento em todas as linhas.

---

## Sprint 7 — Alertas e auditoria contínua

**Objetivo:** detectar vazamentos e desvios antes do fechamento gerencial.

### Entregas

- Alertas de margem, despesas, quebra de caixa, estoque e faturamento.
- Limiares diferentes por departamento.
- Detecção de despesas sem categoria, documento ou departamento.
- Fluxo de reconhecimento, responsável, prazo, justificativa e encerramento.
- Histórico de alterações e evidências.

### Critérios de aceite

- Alertas possuem severidade, impacto estimado e regra reproduzível.
- Nenhum alerta é criado a partir de dado sem cobertura mínima.
- Encerramento exige evidência ou justificativa registrada.

---

## Sprint 8 — Operação, segurança e evolução

**Objetivo:** tornar o produto confiável para uso diário da alta gestão.

### Entregas

- Monitoramento de disponibilidade, latência, paginação e qualidade.
- Rotação e proteção das três credenciais.
- Perfis de Presidência, Diretoria, Auditoria e Operação.
- Backups, retenção, recuperação e runbook de incidentes.
- Relatório diário e fechamento semanal automatizados.
- Processo formal para inclusão de uma nova licença ou departamento.

### Critérios de aceite

- Falhas de API ou dados aparecem antes de afetar decisões.
- Segredos não aparecem em logs, telas ou repositório.
- Inclusão de empresa exige licença, cadastro, teste de contrato e aprovação.

## Backlog prioritário

### P0 — bloqueia confiança

- Confirmar significado dos tipos de produto `C`, `P` e `U`.
- Aprovar o tratamento de COMODATO, DIVERSOS e USO E CONSUMO.
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

Iniciar a **Sprint 1 — Inventário e contrato dos dados WebPosto**. Ela desbloqueia todos os cálculos posteriores e evita construir dashboards visualmente completos com números sem classificação gerencial confiável.
