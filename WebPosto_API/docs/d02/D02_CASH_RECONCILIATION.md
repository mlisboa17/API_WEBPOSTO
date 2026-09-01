# D02 — Cash Reconciliation (Agente 4)

> **Pré-conferência interna (dinheiro/sangria)** — não validação bancária/cofre. [D02_CONCEPTUAL_CORRECTION.md](./D02_CONCEPTUAL_CORRECTION.md)

## Escopo

| Fluxo | Fonte | Evidência |
|---|---|---|
| Dinheiro apresentado vs apurado | CAIXA_APRESENTADO | dinheiro* |
| Sangria | DESPESAS semântico | classe SANGRIA / descrição |
| Fundo de caixa | CAIXA.abertura + fundoCaixaCredito | parcial |
| Depósito | MOVIMENTO_CONTA | histórico DEPOS/SANGRIA |
| Suprimento | MOVIMENTO_CONTA / suprimentoCaixa | parcial |

## Estratégia DINHEIRO

1. Apurado/apresentado via CAIXA_APRESENTADO
2. Sangria total via DESPESAS (ExpenseLineage)
3. Valor esperado = apurado − sangria
4. Diferença operacional = apresentado − apurado (Prestação)
5. Status: AUTO_MATCH se |dif| ≤ R$ 0,01; NEEDS_REVIEW se sangria ≠ apresentado parcial

## Rastreabilidade

Reutiliza `PrestacaoContasIntelligenceService.sangria_intelligence` — sangria vs depósito MOVIMENTO_CONTA.

## Gap

Vínculo 1:1 sangria→depósito bancário permanece parcial (~15% tolerância documentada F03.4-B).
