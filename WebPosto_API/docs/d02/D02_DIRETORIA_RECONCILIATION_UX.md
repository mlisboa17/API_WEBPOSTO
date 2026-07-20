# D02 — Diretoria Reconciliation UX (Agente 8)

> UI **Executivo › Conferência** = pré-conferência interna (rótulo legado). Escopo: [D02_CONCEPTUAL_CORRECTION.md](./D02_CONCEPTUAL_CORRECTION.md)

## Integração

- **Área:** Executivo
- **Aba:** Conferência (`cashReconciliation`)
- **Rota URL:** `/cash-reconciliation`
- **Página:** `frontend/pages/cashReconciliation.js`

## Fluxo Diretoria preservado

```text
Executivo › Alertas (actionCenter) — intacto
Executivo › Conferência — NOVO
```

Orientação: decisão / exceção / ação — não dashboard financeiro tradicional.

## 1ª dobra

KPIs: Valor Apurado | Conferido | Divergente | Pendente

## Detalhe

- Progresso X de Y naturezas
- Cards por natureza com movimento (somente)
- Tabela exceções (NEEDS_REVIEW + DIVERGENT)
- Painel "Insights do Auditor" (audit signals)

## API consumida

`GET /api/v1/cash-reconciliation/summary` via `fetchCashReconciliationSummary`

## Não alterado

- dashboard-v2
- layout global executivo
- módulos VALUE-03/04 detectores
