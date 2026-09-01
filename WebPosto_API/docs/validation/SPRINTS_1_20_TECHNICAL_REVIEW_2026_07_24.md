# Revisão técnica das Sprints 1–20

Data da revisão: 24/07/2026

## Resultado

A implementação departamental foi revisada com foco em segurança, correção,
desempenho e estratégia de testes. A bateria focada terminou com 97 testes
aprovados e 690 testes não selecionados. O JavaScript do painel passou na
verificação de sintaxe e o diff não apresentou erros de whitespace.

A suíte unitária completa não terminou dentro de 180 segundos. Portanto, esta
revisão não declara aprovação integral da suíte legada.

## Correções realizadas

- As rotas que alteram fatos, metas, alertas e auditorias agora exigem
  autenticação e perfil autorizado.
- O autor de ações de governança passa a vir do usuário autenticado, impedindo
  falsificação pelo corpo da requisição.
- O painel escapa dados dinâmicos antes de inseri-los no HTML, reduzindo risco
  de XSS persistente.
- Metas validam datas ISO e rejeitam períodos invertidos.
- Consultas de histórico rejeitam intervalos maiores que 366 dias.
- Foram adicionados testes para autenticação, autorização, leitura pública e
  validações de período.

## Evidências executadas

- 97 testes focados aprovados em 44,92 segundos.
- 21 testes de segurança e validação aprovados em execução isolada.
- Sintaxe do script de `frontend/departmental.html` aprovada pelo Node.js.
- `git diff --check` aprovado nos arquivos revisados.

## Melhorias prioritárias restantes

1. Substituir os arquivos JSON mutáveis por SQLite/PostgreSQL ou implementar
   trava entre processos. Com múltiplos workers, travas locais não eliminam
   totalmente o risco de perda de atualização.
2. Separar avaliação e consulta de alertas: requisições GET não devem persistir
   alterações.
3. Criar cache ou agregados diários para evitar releitura repetida de arquivos
   grandes no cockpit, relatórios e governança.
4. Corrigir a lentidão ou bloqueio da suíte completa, usando marcadores,
   isolamento de integrações externas e limites de tempo por teste.
5. Migrar validadores e configurações legadas para Pydantic 2 antes da remoção
   dessas APIs no Pydantic 3.
6. Remover ou corrigir os arquivos Python inválidos
   `dependencies-mlisboa17.py` e `main-mlisboa17.py`, que hoje geram avisos no
   relatório de cobertura.
7. Executar teste de navegador do fluxo autenticado e observar a primeira
   execução real das automações diária e semanal.

## Próxima bateria recomendada

- Integração: login, gravação de meta, reconhecimento de alerta e ciclo completo
  de auditoria usando armazenamento temporário.
- Navegador: filtros, abas, tratamento de erro e conteúdo vindo do WebPosto.
- Operação: idempotência da coleta diária, execução atrasada de auditorias e
  recuperação após falha parcial.
- Desempenho: tempo e memória do cockpit com todas as empresas e 366 dias.

