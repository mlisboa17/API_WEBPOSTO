# EXPENSE DEDUP ANALYSIS — P0.1-B

## Respostas

### 1. Existem duplicidades?

**Sim.** Duplicidade operacional confirmada no fechamento `caixaCodigo=4343023`.

### 2. Quantas?

**2 duplicidades** na camada de tela (3 linhas operacionais para 1 fechamento):

- 2× `origem=caixa` (R$ 135 + R$ 135)
- 1× `origem=pdv` (R$ 135) — mesmo fato contado como origem distinta

### 3. Quais IDs?

| caixaCodigo | pdvCodigo | turnoCodigo | funcionarioCodigo |
|------------:|----------:|------------:|------------------:|
| 4343023 | 15880 | 1 | 158924 |

### 4. Qual fonte gera a duplicidade?

| Causa | Detalhe |
|-------|---------|
| **Merge dual emit** | `_load_screen_expenses` emitia `caixa_item` **e** `pdv_item` por fechamento |
| **Dedupe fraco** | Chave incluía `descricao` → mesma linha caixa com descrições diferentes passava 2× |
| **Paginação** | Possível repetição de fechamento em `CAIXA_REDE` (mitigado por `_dedupe_closure_source_rows`) |

### 5. O merge atual estava repetindo registros?

**Sim.** Para cada fechamento:

```text
CAIXA_REDE row + CAIXA_APRESENTADO merge
  → linha origem=caixa (apresentado)
  → linha origem=pdv (apurado)    ← mesmo R$ 135
  → segunda linha caixa (descricao alterada pós-match) ← bug dedupe
```

---

## Critério de igualdade aplicado

```text
empresaCodigo + dataMovimento + caixaCodigo + turnoCodigo + pdvCodigo
```

Todos iguais nas 3 linhas operacionais duplicadas.

---

## Correção aplicada

- Uma linha por fechamento: `_normalize_closure_screen_expense()`
- Dedupe operacional por chave de fechamento (sem `descricao`/`valor`)
- Dedupe financeiro separado (`_EXPENSE_DEDUPE_KEYS` com valor/planoConta)
