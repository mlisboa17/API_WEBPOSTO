# Runbook — sync DF-e 118508

## Importação local

1. Colocar XML/ZIP em `data/dfe/inbox/118508/` ou `data/dfe/manual_import/118508/`.
2. `python scripts/dfe_cost_sync_118508.py import-local`
3. Conferir `found`, `imported`, `duplicates`, `invalid`, `quarantined`.
4. Originais permanecem no inbox. Cópias válidas em `data/dfe/processed/118508/`.

## SEFAZ

1. `python scripts/dfe_cost_sync_118508.py status` — ver `cooldown_active` e `last_nsu`.
2. Se cooldown ativo, parar.
3. `python scripts/dfe_cost_sync_118508.py sync-sefaz-once` — uma consulta.
4. cStat 656: registrar, esperar `next_allowed_query_at`, não repetir.
5. Sem documentos (137): encerra normalmente; NSU pode avançar se a persistência foi segura.

## Recálculo

`python scripts/dfe_cost_sync_118508.py recalculate --ean ...`
Só cruza com `pending_cost_update` / `pending_price_review`. Evento `DFE_IMPORTED_COST_REEVALUATED`.

## run-once

Lease → local → SEFAZ se permitido → índice → recálculo dos EANs afetados → libera lease.

## Agendamento

A CLI é idempotente para cron futuro. Esta fase não instala tarefa no Windows.
