# Automação incremental de DF-e

Fase 2: importar NF-e (local e SEFAZ) e recalcular só os EANs afetados. Sem PUT no WebPosto e sem manifestação.

Empresa: **118508**. CNPJ destinatário: **02080237000155**. Ambiente: **PRODUCTION**.

## Fluxo

```
inbox/manual_import
 → hash + validação + store
 → índice de itens
 → EANs afetados ∩ pending_cost_update
 → CostUpdateService.propose(eans)
 → proposta nova / SUPERSEDED
```

## Importação local

Diretórios: `data/dfe/inbox/118508/` e `data/dfe/manual_import/118508/`.
Aceita XML, ZIP, procNFe, resNFe, cancelamento e lotes. O original não é alterado.
Cópia válida vai para `processed`; inválida para `quarantine` com motivo.

## Consulta SEFAZ

Uma página por execução, sempre com o `ultNSU` persistido. Nunca zera o NSU.
`cStat 656` ativa cooldown de 1 hora e não avança NSU.
NSU só muda depois da importação segura.

## Lease

`run-once` adquire lease de 300s. Segunda execução simultânea retorna `LEASE_HELD`.

## Conversão de embalagem

`PackagingConversionResolver` só confirma fator explícito (qTrib UNI, razão inteira, CX12, tabela manual aprovada).
CX/DP/FD sem quantidade e KG sem peso unitário ficam `REVIEW_REQUIRED`.
Descrição pode sugerir, nunca confirmar sozinha.

## Recálculo incremental

Somente EANs do lote ∩ fila pendente. Evento `DFE_IMPORTED_COST_REEVALUATED`.
Proposta antiga vira `SUPERSEDED`. Agregados dos 207 não são reescritos.

## CLI

```bash
python scripts/dfe_cost_sync_118508.py import-local
python scripts/dfe_cost_sync_118508.py status
python scripts/dfe_cost_sync_118508.py sync-sefaz-once
python scripts/dfe_cost_sync_118508.py recalculate --ean ...
python scripts/dfe_cost_sync_118508.py run-once
```

`--execute` é recusado (`COST_UPDATE_WRITES_NOT_IMPLEMENTED`).
