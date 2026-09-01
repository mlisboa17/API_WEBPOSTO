# Decision Evidence Items

## Schema (`DecisionEvidenceItem`)

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| id | string | sim |
| tenant_id | string | sim |
| empresa_codigo | string \| null | não |
| tenant_name | string \| null | não |
| source | string | sim |
| category | string \| null | não |
| person_name | string \| null | não |
| date | string \| null | não |
| amount | number | sim |
| description | string \| null | não |
| origin | string \| null | não |
| cash_register | string \| null | não |
| shift | string \| null | não |
| document_reference | string \| null | não |
| match_status | string \| null | não |
| match_confidence | number \| null | não |
| nominal_source | string \| null | não |
| nominal_source_file | string \| null | não |
| nominal_source_page | number \| null | não |
| nominal_source_reference | string \| null | não |
| matching_reason | string \| null | não |
| beneficiary_vs_review | object \| null | não |
| review_responsible | string \| null | não (sempre null nesta etapa) |
| raw_reference | object | sim |

## Origem dos dados

1. **ExpenseDetector** — ao detectar `CATEGORY_SPIKE`, anexa `evidence_items` em `DecisionCandidate.evidence`.
2. **Fallback** — `DecisionEvidenceService` reconstrói a partir de `snapshots/discovery_expense` se snapshot antigo não tiver items.
3. **Persistência** — `owner_analysis_runner` grava `candidate` completo em `top_5_decisions` e `stored_candidates`.

## Enriquecimento nominal (DIR-01 / DIR-01C)

1. **CAIXA + valeFunApurado** — match operacional por turno (`nominal_matcher.py`).
2. **Prestação de Contas** — fonte complementar via `prestacao_nominal_extractor.py` (markdown/PDF export); agregado mensal; **não** prova financeira externa.

`person_name` = beneficiário do vale · `review_responsible` = responsável pela conferência (workflow futuro).

## Solicitação de conferência (DIR-01D)

Gap nominal → `ExecutiveReviewRequest` via `POST /api/v1/decisions/{id}/review-requests`. Ver `EXECUTIVE_REVIEW_REQUEST.md`.

## API

`GET /api/v1/decisions/{decision_id}/evidence`

Resposta: `decision_summary`, `root_cause`, `money_found`, `confidence`, `evidence_items`, `limitations`, `source_metadata`.

## Ordenação

Maior `amount` primeiro. Total e contagem expostos no payload e na UI.
