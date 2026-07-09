# Director 60 Second Test — Baseline (pré Visão da Rede)

Medição visual real antes da implementação da experiência executiva integrada.

## Runtime

- Frontend: `WebPosto_API/frontend` servido em `http://127.0.0.1:8040/app/financial`
- Rota Diretoria: `?view=owner-diretoria`
- Período: `2026-06-05` a `2026-07-04`
- Evidência: `DIRECTOR_60_SECOND_TEST.json`, screenshot `DIRECTOR_60_SECOND_TEST.png`

## Resultado geral

| Métrica | Valor |
|---------|-------|
| PASS | 1 |
| PARTIAL | 3 |
| FAIL | 4 |

## Perguntas (60 segundos)

| # | Pergunta | Score | Motivo |
|---|----------|-------|--------|
| 1 | Quantos postos foram analisados? | **PASS** | Texto de cobertura parcialmente visível |
| 2 | Qual posto precisa da minha atenção? | **PARTIAL** | Sem hero de prioridade; decisão não destacada |
| 3 | Quanto dinheiro está envolvido? | **FAIL** | Valor de impacto não visível na home |
| 4 | Qual é o principal problema? | **PARTIAL** | Mensagem genérica de análise, sem problema estruturado |
| 5 | Por que isso aconteceu? | **FAIL** | Causa/confiança não visíveis na home |
| 6 | O que devo fazer agora? | **FAIL** | CTA executivo fraco na home |
| 7 | Existe algo que eu já encaminhei? | **PARTIAL** | Follow-up existe na API mas não na home Diretoria |
| 8 | Qual o estado desse encaminhamento? | **FAIL** | Responsável/progresso FIN-03 ausentes na home |

## Maior gap identificado

A home `ownerDiretoriaHome` não integra:

- decisão prioritária em destaque;
- visão dos 3 postos;
- observations do CardReceivableDetector;
- acompanhamento executivo com responsável e progresso;
- separação ESTIMATED vs CONFIRMED.

## Próximo slice

Implementar **Visão da Rede** em `ownerDiretoriaHome.js` reutilizando `top5`, `analysis_proof`, `observations` e `executive/follow-ups`.
