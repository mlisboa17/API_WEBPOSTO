# Sprints 7 e 8 — governança departamental

Data: 2026-07-24

## Entregue

- alertas determinísticos por empresa, departamento, período e regra;
- bloqueio de alerta financeiro quando vendas/custos não têm cobertura;
- margem bruta negativa somente com base completa;
- despesas incompletas tratadas como bloqueio de lucro;
- reconhecimento e encerramento com ator, horário e evidência/justificativa;
- saúde das três empresas sem exposição de credenciais;
- perfis de Presidência, Diretoria, Auditoria e Operação;
- relatório executivo diário e runbook de recuperação;
- visualização em `/app/departmental`, aba **Alertas e saúde**.

## Limites preservados

O sistema não classifica automaticamente uma exceção como deficiência significativa
ou fraqueza material. Essa conclusão exige auditor ou profissional financeiro
qualificado. Limiares financeiros não aprovados não foram inventados.

Retenção destrutiva, restauração e rotação real de credenciais não foram executadas.
Foram documentadas e mantidas sob controle operacional explícito.
