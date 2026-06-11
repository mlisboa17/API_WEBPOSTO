# EXPENSE DEDUP FIX REPORT — P0.1-B

## Problema

Mesmo fechamento de caixa gerava até **3 linhas** na tela (2 caixa + 1 pdv) para R$ 135, inflando caixa para R$ 270.

## Correção

| Arquivo | Mudança |
|---------|---------|
| `network_financial_overview_service.py` | `_normalize_closure_screen_expense()` — 1 linha/fechamento |
| | `_dedupe_closure_source_rows()` — paginação REDE |
| | `_expense_origem_matches()` — filtro pdv inclui fechamento caixa com apurado |
| | Dedupe separado financeiro vs operacional |
| `tests/unit/test_screen_expenses_closure_dedup.py` | Testes novos |

## Chave de dedupe operacional

```text
empresaCodigo + data + caixaCodigo + turnoCodigo + pdvCodigo + funcionarioCodigo
```

## Campos preservados

```text
despesaApurado, despesaApresentado, despesaDiferenca, matchFinanceiro
```

## Não alterado

- `_load_filtered_expenses()` (Finance Center / overview)
- Cash Flow, Cash Operations, Supplier Intelligence

## Resultado AP CASA CAIADA 08/06/2026

| | Antes | Depois |
|---|------:|-------:|
| Caixa | 2 · R$ 270 | **1 · R$ 135** |
| PDV | 1 · R$ 135 | **0 linhas separadas** |
| Total | 5 · R$ 2.317 | **3 · R$ 2.047** |
