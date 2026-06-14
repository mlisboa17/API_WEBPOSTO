# IA-5 — Frontend Regression Audit (UX-01)

## Escopo comparado

| Arquivo UX-01 | Impacto em Financeiro |
|---------------|----------------------|
| `navigation.js` | Receitas→`dashboard`, Despesas→`expenses` — **correto** |
| `navigationShell.js` | Troca área/view via `setView()` — **sem alterar endpoints** |
| `app.js` | Mesmos `fetchFinancialOverview` / `fetchFinancialExpenses` |
| `api.js` | Rotas `/v1/financial/overview` e `/v1/financial/expenses` **inalteradas** |

## O que UX-01 mudou

- Sidebar: 33 botões → 6 macro áreas
- `dashboard` movido de área Executivo para **Financeiro → Receitas**
- Motores ocultos da home — **não afeta chamadas API**

## O que UX-01 NÃO mudou

- Funções de fetch financeiro
- URLs de API
- Services backend
- Circuit breaker
- Mensagem de erro

## Evidência runtime

Com navegação atual, as mesmas rotas backend falham:

```
GET /v1/financial/overview  → CIRCUIT_OPEN (despesas_financeiro_rede)
GET /v1/financial/expenses  → CIRCUIT_OPEN (despesas_financeiro_rede)
```

Isso ocorreria **independentemente** da sidebar — qualquer cliente chamando estas rotas recebe o mesmo erro.

## Parecer IA-5

**Sem regressão UX-01 comprovada.** A reorganização da sidebar **não quebrou rotas** — apenas tornou mais visível um bloqueio backend pré-existente ao acessar Financeiro diretamente.
