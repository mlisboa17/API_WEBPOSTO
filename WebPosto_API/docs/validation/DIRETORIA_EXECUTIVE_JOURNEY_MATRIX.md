# Diretoria — Matriz da Jornada Executiva

**Auditoria:** DIRETORIA FINAL · 2026-07-07  
**Branch:** `feature/build-03-trust-home` · commit `e63fb5e`

Legenda: **PASS** = comprovado em runtime/código · **PARTIAL** = funciona com lacuna de experiência · **N/A** = fora do escopo Diretoria

| Etapa | Rota / view | Endpoint | Fonte dos dados | Estado runtime | CTA | Destino | Dead-end? | Sucesso falso? | Mock? | Conclusão sem evidência? |
|---|---|---|---|---|---|---|---|---|---|---|
| **ENTRADA** | App → área Executivo | — | SPA `frontend/app.js` | Carrega filtros + navegação | Tabs Decisões / Em acompanhamento | `ownerDiretoriaHome` / `executiveFollowUp` | Não | Não | Não | N/A |
| **HOME EXECUTIVA** | `?view=owner-diretoria` → `#ownerDiretoriaHomeView` | `GET /api/v1/owner-action-center/top5` | Snapshot `owner_analysis_last_valid_*` + refresh background | `monitoring_state=DECISION`, `analysis_status=PRIORITY_FOUND`, 1 decisão | Atualizar análise | refresh endpoint | Não | Não | Não | Não — decisão vem de ExpenseDetector + baseline |
| **DECISÃO (lista)** | Card na Home | (payload top5) | Discovery Engine / snapshot DIR01 | Winner ExpenseDetector · 74014 · R$ 7.501 ESTIMATED | Abrir decisão | `decisionDetail` | Não | Não | Não | Não |
| **CAUSA** | Seção "Causa provável" em `decisionDetail` | (inline no GET evidence) | `ExpenseRootCause.investigate` via `DecisionEvidenceService._root_cause_text` | Texto: "Maior volume de lançamentos em Vale…" | — | — | Não | Não | Não | Não — causa derivada de evidência agregada |
| **EVIDÊNCIA** | Tabela "Evidências da decisão" | `GET /api/v1/decisions/{id}/evidence` | WebPosto DESPESAS + enrichment nominal CAIXA/Prestação | 16 itens · R$ 8.401 · tenant 74014 only | Ver descrição (expand) | inline | Não | Não | Não | Não — soma bate total |
| **AÇÃO EXECUTIVA** | Bloco "Identificação nominal" | — | Cálculo client-side NO_MATCH+AMBIGUOUS sem `person_name` | 13 pendentes · R$ 7.951 | Solicitar conferência | POST review-request | Não | Não | Não | Não |
| **SOLICITAÇÃO** | POST + estado "Conferência solicitada" | `POST/GET .../review-requests` | `ExecutiveReviewStore` → `snapshots/executive_review_requests/store.json` | `REQUESTED`, `review_responsible=null` | — | — | Não | Não (erro HTTP → alerta UI) | Não | Não |
| **ACOMPANHAMENTO** | `?view=executive-follow-up` | `GET /api/v1/executive/follow-ups` | Projeção `ExecutiveFollowUpItem` | active_count=1 · R$ 7.951 | Ver acompanhamento | `executiveFollowUpDetail` | Não | Não | Não | Não |
| **DETALHE FOLLOW-UP** | `?view=executive-follow-up-detail` | `GET /api/v1/executive/follow-ups/{id}` | store + decisão enriquecida | Aguardando atribuição | Ver decisão original | `decisionDetail` | Não | Não | Não | Não |
| **RETORNO À DECISÃO** | `decisionDetail` ← follow-up | GET evidence + review-requests | snapshot decisão + store | Mesma decisão 175da101… | Voltar à Home | `ownerDiretoriaHome` | Não | Não | Não | Não |

## Estados Home (contratos)

| Estado | Backend comprovado | UI Diretoria | Avaliação |
|---|---|---|---|
| **DECISION** | SIM — snapshot DIR01 + VALUE-04 winner | Card prioritário + CTA Abrir | **PASS** |
| **OBSERVATION** | SIM — VALUE-04 (2 observações CardReceivable) | **Não renderiza lista de observations** em `ownerDiretoriaHome.js` | **PARTIAL** — API entrega; UI omite |
| **NORMAL** | SIM — snapshot FuelRevenue all (message sem prioridade) | Empty state com mensagem neutra (não "negócio sob controle") | **PASS** |

## Cobertura / limitações visíveis

| Elemento | Backend (`analysis_proof`) | UI Home | Avaliação |
|---|---|---|---|
| Tenants analisados | SIM — snapshots multi-tenant | Oculto quando há decisão e `limitations` vazio no seed DIR01 | **PARTIAL** |
| Detectores executados | SIM | Só em empty state ou `<details>` se houver limitations | **PARTIAL** |
| Áreas não analisadas | SIM (`limitations`, tenant FAILED) | Parcialmente via `<details>` | **PARTIAL** |

## Navegação crítica (sem dead-end)

```
Decisões → Abrir decisão → Solicitar conferência → Em acompanhamento → Ver acompanhamento → Ver decisão original → Voltar
```

**Resultado:** jornada principal **completa** · gaps de **visibilidade** (observations, analysis_proof, root cause estendido) não bloqueiam o fluxo executivo no cenário DECISION atual.
