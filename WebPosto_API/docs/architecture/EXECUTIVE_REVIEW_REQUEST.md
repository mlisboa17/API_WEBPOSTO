# ExecutiveReviewRequest — Arquitetura

## Fronteira Diretoria → Financeiro

`ExecutiveReviewRequest` é a **fronteira** entre:

| Módulo | Papel |
|--------|-------|
| **Diretoria** | Detecta gap · entende evidência · **solicita** conferência |
| **Financeiro** (futuro) | Recebe · confere · documenta · **responde** |

Nesta entrega implementa-se **apenas o lado Diretoria**.

## Auditoria de estruturas existentes

| Estrutura | Reutilizada? | Motivo |
|-----------|--------------|--------|
| `DecisionAction` (Owner Intelligence) | Não | Sugestão de UI, sem persistência de solicitação |
| `ExecutionRecord` (decision_execution) | Não | Ciclo execute/confirm — semântica diferente |
| `ReconciliationStateStore` (D02) | **Padrão** | JSON em `snapshots/` — replicado |
| `ExecutiveReviewRequest` | **Nova** | Entidade mínima isolada |

## Contrato

Campos principais: `decision_id`, `request_type`, `status`, `evidence_item_ids`, contagens/valores identificados vs pendentes, `review_responsible` (null nesta etapa).

### request_type

- `NOMINAL_IDENTIFICATION_REVIEW`

### status (lifecycle)

`REQUESTED` → `ASSIGNED` → `IN_REVIEW` → `NEEDS_INFORMATION` → `COMPLETED` | `CANCELLED`

Statuses **ativos** (idempotência): `REQUESTED`, `ASSIGNED`, `IN_REVIEW`, `NEEDS_INFORMATION`.

## Persistência

`ExecutiveReviewStore` → `snapshots/executive_review_requests/store.json`

Sobrevive a restart HTTP; não usa mock nem variável global volátil.

## API

| Método | Path |
|--------|------|
| POST | `/api/v1/decisions/{decision_id}/review-requests` |
| GET | `/api/v1/decisions/{decision_id}/review-requests` |
| GET | `/api/v1/review-requests/{request_id}` |

## Regra de itens pendentes

Entram na solicitação apenas evidence_items com `match_status` ∈ `{NO_MATCH, AMBIGUOUS}` **e** sem `person_name`.

PROBABLE/EXACT com beneficiário identificado **não** entram.

## Idempotência

Chave lógica: `decision_id` + `request_type` + status ativo. Segundo POST retorna `already_exists: true` (HTTP 200).
