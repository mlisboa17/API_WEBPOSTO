# Financial Review Inbox — FIN-01

## Decisão arquitetural (Fase 0)

**Reutilizar `ExecutiveReviewRequest` + `ExecutiveReviewStore`.**

| Pergunta | Resposta |
|----------|----------|
| Nova entidade persistida? | **Não** |
| Novo store? | **Não** |
| Duplicar solicitação? | **Não** |

### Projeções sobre a mesma solicitação

```
ExecutiveReviewRequest (store.json)
        |
        +---- ExecutiveFollowUpItem     → visão Diretoria ("Em acompanhamento")
        |
        +---- FinancialReviewInboxItem  → visão Financeiro ("Conferências")
```

Implementação: `src/services/executive_review/financial_inbox.py`

## API

| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/api/v1/financial/review-inbox` | Lista ativa (filtros: `status`, `tenant_id`, `request_type`) |
| GET | `/api/v1/financial/review-inbox/{request_id}` | Detalhe + `pending_evidence_items` |

## Ordenação inbox

1. `PRIORITY_RANK` (campo `priority` da request — hoje `NORMAL`)
2. `amount_under_review` DESC
3. `requested_at` ASC

## Labels financeiros

Mapeados em `financial_status_label()` — ex.: `REQUESTED` → **Aguardando análise** (distinto do label executivo "Aguardando atribuição").

## Fronteira

FIN-01 **não** implementa mutações (assumir, atribuir, concluir). Apenas leitura operacional.

FIN-02 adiciona **POST assign** — ver `FINANCIAL_REVIEW_ASSIGNMENT.md`.

## Performance detalhe

Detalhe financeiro usa `enrich_nominal=False` — carrega evidence do snapshot local filtrado por `evidence_item_ids` da request, sem re-enrichment WebPosto live.

## UI

- Área **Financeiro** → aba **Conferências**
- Rotas: `?view=financial-review-inbox` · `?view=financial-review-detail&requestId={id}`
