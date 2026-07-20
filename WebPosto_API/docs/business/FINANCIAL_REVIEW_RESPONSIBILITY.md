# Financial Review Responsibility — FIN-02

## Fronteira de papéis

| Papel | FIN-01 | FIN-02 | Próximo |
|-------|--------|--------|---------|
| Diretoria | Solicita conferência | Acompanha responsável atribuído | Recebe resposta (futuro) |
| Financeiro | Recebe e abre fila | **Assume responsabilidade** | Confere e documenta (futuro) |

## Fluxo FIN-02

1. Financeiro abre Conferências → detalhe da solicitação.
2. Status **Aguardando análise**, responsável **Ainda não atribuído**.
3. Clica **Assumir conferência**.
4. Informa **nome do responsável** (sem inferir usuário logado).
5. POST `/assign` → status **Atribuído**, responsável persistido.
6. Diretoria vê automaticamente em **Em acompanhamento** — mesma request.

## Identidade

O LOGOS **não possui** autenticação de usuário real nesta sprint.

O responsável é o nome **explicitamente digitado** pelo operador financeiro.

Proibido: "Usuário atual", "Financeiro", "Admin".

## Mensagens

- Sucesso **somente após HTTP 2xx**: "Conferência atribuída com sucesso."
- Conflito: exibir erro da API (409).

## FIN-02 ainda NÃO

- Conferir lançamentos
- Anexar comprovantes
- Concluir solicitação
- Responder Diretoria
