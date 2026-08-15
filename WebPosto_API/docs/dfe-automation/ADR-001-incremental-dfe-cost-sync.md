# ADR-001 — Ingestão incremental e recálculo

## Contexto

A fase 1 achou 195 pendências sem DF-e. Entrar nota e recalcular os 207 inteiros a cada arquivo é desperdício e risco.

## Decisão

Orquestrador `DfeCostSyncService` sobre `import_files` + `CostUpdateService.propose(eans=...)`. Lease, cooldown e NSU pós-persistência.

## Consequências

- Recálculo só dos EANs do lote ∩ fila pendente.
- Proposta antiga vira SUPERSEDED.
- Conversão de embalagem exige fator explícito; CX/DP sem número continua REVIEW.
