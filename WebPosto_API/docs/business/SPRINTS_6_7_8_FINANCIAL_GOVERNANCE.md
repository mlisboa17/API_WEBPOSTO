# Sprints 6, 7 e 8 — Governança Financeira

## Sprint 6 — Classificação departamental governada

- Classificação por evidência textual explícita do WebPosto.
- Registro do método, evidências e confiança em cada fato.
- Confiança automática fixada em 0,90 para evidência única.
- Evidências de departamentos diferentes geram conflito e revisão obrigatória.
- Ausência de evidência permanece sem classificação; o sistema não adivinha.
- Resumo de governança informa classificados, não classificados e conflitos.

## Sprint 7 — Alertas executivos

- Cobertura incompleta gera bloqueio crítico.
- Quarentena e duplicidade geram alertas de severidade alta.
- Correspondência provável e ausência de vínculo geram alertas médios.
- Cada alerta informa empresa, departamento, ocorrências e ação recomendada.
- Alertas não acusam fraude e nunca geram lançamento ou impacto automático na DRE.
- A tela apresenta totais de alertas críticos, altos e médios.

## Sprint 8 — Prontidão operacional

- Snapshot com TTL de cinco minutos.
- Reutilização de snapshot válido para abertura rápida da tela.
- Fallback stale quando a atualização falha e existe evidência anterior.
- Endpoint `POST /api/v1/finance/director-reconciliation/refresh`.
- O botão de atualização força nova coleta.
- Tempo total do pipeline incluído no payload de desempenho.

## Gate concluído

- 29 testes aprovados.
- Sintaxe JavaScript validada.
- Somente as empresas 11495, 5555 e 74014 permanecem autorizadas.
- Combustíveis, Conveniência e Lubrificantes continuam independentes.
