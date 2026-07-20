# D02 — Reconciliation Domain Contract

> **D02 — Reconstrução da Prestação e Pré-Conferência Interna** · [D02_CONCEPTUAL_CORRECTION.md](./D02_CONCEPTUAL_CORRECTION.md)

Barreira de implementação — consolida Agentes 1–5.

## Entidades

| Entidade | Responsabilidade |
|---|---|
| PaymentNature | O que o valor representa (15 códigos) |
| CaptureOrigin | Como entrou (TEF, POS_MANUAL, …) |
| ExpectedDestination | Onde deveria liquidar |
| ReconciliationEvidence | Evidência interna ligada à expectativa (não prova externa) |
| ReconciliationItem | Unidade conferível (filial/caixa/turno/natureza) |
| JustificationRecord | Histórico imutável append-only |
| AuditSignal | Sinal determinístico pós-conferência |

## Estados

`NOT_REVIEWED | IN_REVIEW | AUTO_MATCHED | NEEDS_REVIEW | DIVERGENT | JUSTIFIED | CONFIRMED`

## Pré-conferência

Motor: `PreReconciliationEngine` — classifica sem revisão humana total.

## API (FastAPI)

| Método | Rota | Função |
|---|---|---|
| GET | `/api/v1/cash-reconciliation/summary` | Dashboard pré-conferência interna |
| GET | `/api/v1/cash-reconciliation/exceptions` | Exceções prioritárias |
| GET | `/api/v1/cash-reconciliation/audit-signals` | Sinais auditoria |
| POST | `/api/v1/cash-reconciliation/justify` | Registrar justificativa |
| POST | `/api/v1/cash-reconciliation/confirm` | Confirmar item |
| GET | `/api/v1/cash-reconciliation/parity` | Dados API para QA |

## Persistência

- Snapshots: `snapshots/cash_reconciliation/` (TTL 300s)
- Estado decisão: `snapshots/reconciliation_state/` (justificativas append-only)

## Frontend

- View: `cashReconciliation` — área Executivo › Conferência
- Sem acesso Supabase direto

## Invariantes

1. POS/TEF nunca são PaymentNature
2. Adquirente desconhecida = UNKNOWN
3. Zero mock como dado real
4. PDF = oráculo paridade (script QA), não hardcode app
