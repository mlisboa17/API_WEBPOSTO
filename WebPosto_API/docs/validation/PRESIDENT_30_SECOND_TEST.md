# President 30 Second Test — Presidência 2.0

Protocolo de leitura executiva para Presidente/Diretor na entrada padrão do `executive-web`.

## Runtime

- Frontend: `executive-web` em `http://127.0.0.1:3000/` (ou proxy via backend)
- Período sugerido: `start=2026-07-01&end=2026-07-18`
- Evidência: `PRESIDENT_30_SECOND_TEST.json`
- Telemetria: eventos anônimos via `/api/executive-adoption`

## Instruções ao participante

1. Abrir a Presidência 2.0 sem navegar para “Análises detalhadas”.
2. Ler apenas o que aparece nos quatro blocos por **30 segundos**.
3. Responder às quatro perguntas abaixo sem rolar a página além do necessário.
4. Registrar cliques nos títulos dos blocos (telemetria automática).

## Perguntas (30 segundos)

| # | Pergunta | Bloco | Critério PASS |
|---|----------|-------|---------------|
| 1 | O que exige minha atenção hoje? | ATTENTION | Risco concreto com confiança ou mensagem de insuficiência explícita |
| 2 | Onde está o maior valor potencial? | VALUE | Oportunidade com ação sugerida ou bloqueio honesto |
| 3 | Quanto valor a IA já comprovou? | AI_VALUE | Valor **validado** separado do estimado |
| 4 | Quais decisões imediatas existem? | PRESIDENCY_ANSWERS | Resposta estruturada ou “evidências insuficientes” |

## Métricas de adoção (automáticas)

Após a sessão, consultar:

```http
GET /api/v1/departmental-governance/executive-adoption/summary
GET /api/v1/departmental-governance/executive-adoption/block-review
```

Indicadores:

- `averageTimeToInformationMs` ≤ 30000
- `withinThirtySecondTarget: true`
- blocos com `engagement: ENGAGED` nos quatro blocos da presidência

## Baseline estrutural (pré-teste com usuário)

| Métrica | Valor esperado |
|---------|----------------|
| Blocos visíveis na entrada | 4 |
| Valor estimado rotulado | Sim (`ESTIMATED_NOT_REALIZED`) |
| Valor comprovado rotulado | Sim (`VALIDATED_VALUE_ONLY`) |
| Oportunidade inventada sem evidência | Não permitido |

## Resultado do teste estrutural

| # | Pergunta | Score | Motivo |
|---|----------|-------|--------|
| 1 | O que exige minha atenção hoje? | **PASS** | Bloco ATTENTION com lista ou mensagem de insuficiência |
| 2 | Onde está o maior valor potencial? | **PASS** | Bloco VALUE com oportunidades ou bloqueio honesto |
| 3 | Quanto valor a IA já comprovou? | **PASS** | Gráfico comprovado vs estimado com rótulos distintos |
| 4 | Quais decisões imediatas existem? | **PASS** | Perguntas da Presidência com respostas ou insuficiência |

**Scores:** PASS 4 · PARTIAL 0 · FAIL 0 (baseline de arquitetura Sprint 42/43)

## Próximo passo

Executar sessão real com Presidente/Diretor, comparar `block-review` e ajustar copy
somente nos blocos com `IGNORED` ou tempo > 30s — nunca inventando oportunidades.
