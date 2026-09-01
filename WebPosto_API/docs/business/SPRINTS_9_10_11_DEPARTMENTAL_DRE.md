# Sprints 9, 10 e 11 — Validação e DRE Departamental

## Sprint 9 — Validação real

Período controlado: 01/07/2026, três empresas licenciadas.

- Cobertura das fontes: completa.
- Despesas financeiras: 23.
- Títulos a pagar: 46.
- Despesas de caixa apuradas: 0.
- Movimentos de conta recuperados por cursor: 1.319.
- Tempo da primeira coleta: aproximadamente 27 segundos.
- Classificação departamental comprovada das despesas: 0 de 23.

Conclusão: a API está coberta, mas o endpoint de despesas não prova o departamento.
Os 23 registros permanecem em revisão. Movimentos de tesouraria não são tratados
como pendência departamental.

## Sprint 10 — Revisão auditável

- Identificador estável para fatos sem código explícito.
- Persistência de departamento, responsável, justificativa e data.
- Classificação manual usa método `MANUAL_REVIEW` e confiança 1,00.
- `GET /api/v1/finance/director-reconciliation/department-reviews` lista decisões.
- `POST /api/v1/finance/director-reconciliation/department-reviews` registra e recalcula.
- A evidência original continua preservada.

## Sprint 11 — DRE departamental segura

- Endpoint `GET /api/v1/finance/director-reconciliation/dre`.
- Linhas independentes por empresa e por Combustíveis, Conveniência e Lubrificantes.
- Cobertura da API e completude departamental são gates diferentes.
- A DRE só é liberada quando ambos os gates estão completos.
- Com os dados reais avaliados, permanece bloqueada até revisar as 23 despesas.

## Gate de qualidade

- 14 testes focados aprovados após o ajuste final de prontidão.
- Cobertura completa não libera DRE com despesa sem departamento.
