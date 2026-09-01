# Sprints 3, 4 e 5 — Conciliação Financeira

## Sprint 3 — Cobertura por partições

Entregue:

- Partição obrigatória por empresa licenciada e dia.
- Paginação por `ultimoCodigo` em `MOVIMENTO_CONTA`.
- Cursor configurável por endpoint (`movimentoContaCodigo`).
- Rejeição de 5333 e qualquer empresa fora de 11495, 5555 e 74014.
- Interrupção segura para cursor parado, limite de segurança e vazamento de tenant.
- Evidência por partição: empresa, data, páginas, registros e término.

Descoberta confirmada: `empresaCodigo` e `ultimoCodigo` são aceitos por
`MOVIMENTO_CONTA`; `pagina`, `tamanhoPagina` e `filial` não oferecem paginação
confiável nesse endpoint.

## Sprint 4 — Pipeline auditável

Entregue:

- Normalização de DESPESAS_FINANCEIRO_REDE, TITULO_PAGAR, CAIXA_APRESENTADO e
  MOVIMENTO_CONTA para fatos Pydantic.
- Conciliação conservadora com cinco estados.
- Filtro obrigatório das três licenças.
- Classificação departamental somente por evidência inequívoca; demais registros
  ficam em `nao_classificado`.
- Endpoint `GET /api/v1/finance/director-reconciliation`.
- Payload bruto não é exposto.
- Publicação de totais bloqueada quando a cobertura estiver incompleta.

## Sprint 5 — Visão executiva

Entregue:

- Painel “Conciliação para a Diretoria” no Centro Financeiro.
- Linhas independentes por empresa e por Combustíveis, Conveniência e Lubrificantes.
- Os três departamentos permanecem visíveis mesmo quando zerados.
- Valor confirmado fica oculto quando a cobertura não foi comprovada.
- Colunas separadas para confirmados, prováveis, quarentena e sem vínculo.
- Indicador visual de “Cobertura comprovada” ou “Totais bloqueados”.

## Gate de qualidade

- 22 testes integrados aprovados.
- Sintaxe validada em `frontend/app.js`, `frontend/services/api.js` e
  `frontend/pages/financeCenter.js`.
- Nenhuma correspondência provável entra automaticamente na DRE.
