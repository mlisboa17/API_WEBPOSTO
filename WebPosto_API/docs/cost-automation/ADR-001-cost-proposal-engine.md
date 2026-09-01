# ADR-001 — Motor de proposta de custo

## Contexto

205 produtos da 118508 ficaram com custo pendente no cadastro. O PUT de custo ainda é proibido. É preciso comparar o custo atual (GET) com o custo da NF-e local e gerar propostas auditáveis.

## Decisão

Fachada `CostUpdateService` em `src/operational/cost_update/`. Cálculo reutilizado de `DfeCostResolver`. Escrita WebPosto ausente: portas lançam `COST_UPDATE_WRITES_NOT_IMPLEMENTED`.

## Alternativas

1. **PUT imediato.** Rejeitada: irreversível sem gate.
2. **Recalcular a fórmula no atualizador.** Rejeitada: divergiria do cadastro.
3. **Proposta read-only sobre o resolver comprovado (escolhida).**

## Consequências

- `pending_cost_update` original não é reescrito.
- Checkpoint não substitui o GET.
- Relatórios operacionais ficam em `data/cost_update/` e fora do Git.
