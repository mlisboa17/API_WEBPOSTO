# Financial Review Assignment — FIN-02

## Objetivo

Primeiro ato operacional do Financeiro: **assumir responsabilidade** sobre uma `ExecutiveReviewRequest`.

## Transição

```
REQUESTED → ASSIGNED
```

| Campo | Antes | Depois |
|-------|-------|--------|
| `status` | REQUESTED | ASSIGNED |
| `review_responsible` | null | nome informado explicitamente |
| `assigned_at` | null | timestamp UTC |
| `updated_at` | — | atualizado |

## API

```
POST /api/v1/financial/review-inbox/{request_id}/assign
```

Body:

```json
{ "responsible_name": "Marcio de Lima" }
```

Respostas:

| Código | Situação |
|--------|----------|
| 200 | Atribuído ou idempotente (mesmo responsável) |
| 404 | Request inexistente |
| 409 | Conflito (já atribuída a outro) ou status não permite |
| 422 | Nome vazio |

## Regras

- **Sem autenticação fictícia** — `responsible_name` vem do body, informado pelo operador.
- **Idempotência** — mesmo responsável em request já ASSIGNED → 200, `idempotent: true`.
- **Conflito** — responsável diferente em request ASSIGNED → 409, sem overwrite.
- **Persistência** — `ExecutiveReviewStore` (mesma fonte FIN-01).

## Projeções

Financeiro e Diretoria leem a **mesma request** atualizada:

- `FinancialReviewInboxItem` → label **Atribuído**
- `ExecutiveFollowUpItem` → label **Responsável definido**

Sem sincronização, cópia ou POST para Diretoria.

## Performance (detalhe)

`get_inbox_detail` usa `get_evidence(..., enrich_nominal=False)` — evita chamadas live WebPosto no cold path; IDs já persistidos na request.

## Fora de escopo FIN-02

Conferir, anexar, concluir, responder Diretoria.
