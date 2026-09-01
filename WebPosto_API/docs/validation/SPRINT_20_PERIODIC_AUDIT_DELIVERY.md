# Sprint 20 — auditoria periódica

Data: 2026-07-24

## Entregue nesta rodada

- persistência movida de `snapshots` público para `.runtime/periodic_audits`;
- gravação atômica de ciclos e execuções;
- validação estrita das três empresas licenciadas;
- criação idempotente de ciclos e execuções;
- validação de períodos;
- eventos `OPENED`, `ITEM_RESOLVED` e `APPROVED` com ator, horário e evidência;
- aprovação bloqueada enquanto existir item pendente;
- executor automático de ciclos vencidos;
- seis agendas semanais, Pista e Conveniência por empresa, com corte em 27/07/2026;
- rotina de segunda-feira atualizada para abrir ciclos vencidos;
- aba **Auditorias** na tela `/app/departmental`.

## Controles preservados

- nenhuma baixa ou lançamento financeiro automático;
- ausência de centro de custo não é rateada;
- grupos WebPosto são preservados;
- o sistema registra exceções para revisão e não declara automaticamente deficiência
  significativa ou fraqueza material;
- revisão de auditor ou profissional financeiro qualificado permanece obrigatória.
