# DIR-01D — Ação Executiva: Solicitar Conferência

## Produto

Quando o LOGOS **não** consegue identificar beneficiário nominal suficiente, o gap vira ação executiva real:

**Solicitar conferência** — sem adivinhar funcionário, sem match forçado.

## Linguagem executiva (UI)

Usar: "Solicitar conferência", "lançamentos sem identificação nominal", "Aguardando atribuição", "Valor em revisão".

Evitar: "fraude", "desvio", "perda confirmada", "funcionário responsável".

## Caso VALUE-03 (74014)

- 16 evidence_items · R$ 8.401
- 3 identificados (R$ 450) — **fora** da solicitação
- 13 pendentes (R$ 7.951) — **dentro** da solicitação (10 NO_MATCH + 3 AMBIGUOUS)

R$ 7.951 = valor **sem identificação nominal**, não perda confirmada.

## O que o diretor faz

1. Abre decisão na Home Diretoria
2. Vê evidências e gap nominal
3. Clica **Solicitar conferência**
4. Recebe confirmação real (HTTP 2xx) — status **Aguardando atribuição**

## O que NÃO foi implementado

Inbox financeiro, atribuição de responsável, resposta da conferência, notificações.

O módulo Financeiro consumirá `ExecutiveReviewRequest` futuramente.
