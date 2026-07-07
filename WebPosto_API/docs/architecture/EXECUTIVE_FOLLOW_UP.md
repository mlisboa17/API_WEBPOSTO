# Executive Follow-Up — Arquitetura

## Três conceitos distintos

| Conceito | Papel |
|----------|-------|
| **ExecutiveReviewRequest** | Contrato de **delegação** (Diretoria solicita) |
| **Executive Follow-Up** | Visão executiva de **acompanhamento** (Diretoria observa) |
| **Financeiro (futuro)** | Consumidor **operacional** da solicitação |

## Projeção

`ExecutiveFollowUpItem` — derivado de `ExecutiveReviewRequest` + metadados da decisão (título/categoria via snapshot owner).

**Sem** store duplicado. **Sem** nova entidade persistida.

## API

`GET /api/v1/executive/follow-ups` — lista ativa (REQUESTED, ASSIGNED, IN_REVIEW, NEEDS_INFORMATION)

`GET /api/v1/executive/follow-ups/{request_id}` — detalhe executivo

Filtros: `status`, `tenant_id`, `request_type`

## Frontend

Rota Diretoria: `?view=executive-follow-up` (tab **Em acompanhamento**)

Detalhe: `?view=executive-follow-up-detail&followUpRequestId=…`

Implementação em `WebPosto_API/frontend` (mesmo bundle servido pela API).
