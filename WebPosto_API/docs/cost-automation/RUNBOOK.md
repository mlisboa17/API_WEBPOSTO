# Runbook — propostas de custo 118508

## Scan

Lê `pending_cost_update_118508.json` e `pending_price_review_118508.json` sem alterá-los. Confere o produto por GET. Resolve DF-e no store local.

## Propose

Classifica e grava em `data/cost_update/118508/` (fora do Git). Idempotência por `proposal_hash`.

## Recuperação

Se o GET falhar: o item vai para BLOCKED. Não reenviar escrita — não há escrita.

## Erros CLI

| Código | Significado |
| --- | --- |
| 0 | dry-run ok |
| 1 | proposta não encontrada |
| 3 | empresa ≠ 118508 |
| 5 | `--execute` recusado |

## Próximo passo seguro

Revisar `REVIEW_REQUIRED` e `PROPOSED`. Só então desenhar o gate de PUT, em fase própria.
