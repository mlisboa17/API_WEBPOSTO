# FILTER_AUDIT_REPORT — Sprint P0

**Gerado:** 2026-06-08T12:59:15
**Período:** 2026-06-01 .. 2026-06-07

| Variante | empresaCodigo | Registros | Valor | Empresas | Snapshot |
|---|---|---:|---:|---|---|
| single_11495 | 11495 | 71 | 24676.71 | 11495 | False |
| multi_11495_5555 | 11495,5555 | 415 | 127315.20 | 5256,5333,5555,5556,5557... | False |
| todos_vazio | (vazio) | 415 | 127315.20 | 5256,5333,5555,5556,5557... | False |
| todos_all | all | 415 | 127315.20 | 5256,5333,5555,5556,5557... | False |
| todos_todos | todos | 415 | 127315.20 | 5256,5333,5555,5556,5557... | False |

## Conclusões

- Filtro **single 11495**: 71 registros, apenas empresa 11495 — **OK**
- Sem filtro / `all` / `todos`: 415 registros, 10 filiais — **OK** (visão rede)
- **Multiselect `11495,5555`**: 415 registros, empresas `5256,5333,5555,5556,5557...` — **BUG PROVADO**

### Bug multiselect (P0 backend)

Quando `empresaCodigo=11495,5555`:

| Esperado | Obtido |
|---|---|
| ~71 + despesas 5555 (2 filiais) | 415 registros de **10 filiais** |

**Causa:** `_expense_matches()` só filtra por `filters.empresa_codigo` (single). Em multiselect, `empresa_codigo=None` e o loop por filial recebe **427 rows da rede inteira** da API — todas passam no match. Dedupe reduz para 415, mas **não restringe às filiais selecionadas**.

**Evidência:** `multi_11495_5555` = `todos_vazio` (415 / R$ 127.315,20) — multiselect equivale a "todas".

## API WebPosto — empresaCodigo ignorado em DESPESAS_REDE

Evidência: parâmetro `empresaCodigo=11495` ainda retorna todas filiais na API bruta.
Backend LOGOS filtra client-side — **não é filtro duplicado**, é compensação.

## Refresh / URL

- Filtros persistem via query string (app.js parseUrlFilterValue / serializeUrlFilterValue)
- Multiselect empresa: vírgula na URL
- `__ALL__` / vazio = todas empresas no backend
