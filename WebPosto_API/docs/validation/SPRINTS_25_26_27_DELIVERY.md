# Entrega das Sprints 25, 26 e 27

Data: 24/07/2026

## Sprint 25 — Persistência concorrente

- Stores mutáveis de metas, alertas e auditorias usam trava entre processos.
- A troca atômica dos arquivos foi preservada.
- Locks abandonados possuem recuperação por tempo.
- A abertura de auditoria repete a verificação de idempotência dentro da trava.
- Teste concorrente confirmou que seis gravações paralelas foram preservadas.

## Sprint 26 — Consultas somente leitura

- `GET /api/v1/departmental-governance/alerts` apenas consulta o último estado.
- `GET /api/v1/departmental-governance/daily-report` não gera alertas.
- `POST /api/v1/departmental-governance/alerts/evaluate` realiza a avaliação
  autenticada e persistente.
- O relatório informa quando uma avaliação é necessária.
- A automação diária foi atualizada para avaliar alertas antes de consultar o
  relatório.

## Sprint 27 — Segurança de produção

- Produção rejeita debug, chave JWT fraca, tokens padrão, senha sem hash, cookie
  inseguro e CORS curinga.
- Cookies de autenticação respeitam `AUTH_COOKIE_SECURE`.
- Origens CORS são explícitas e configuráveis.
- O perfil do usuário é preservado ao renovar o token.
- `.env.example`, roadmap e runbook foram atualizados.

## Validação

- 30 testes focados aprovados.
- Compilação dos módulos alterados aprovada.
- `git diff --check` aprovado.
- Permanecem avisos legados de Pydantic/FastAPI e dois arquivos Python inválidos
  já registrados na revisão técnica anterior.

