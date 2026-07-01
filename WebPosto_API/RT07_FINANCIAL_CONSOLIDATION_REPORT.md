# RT-07 — IA-3: Financial Consolidation

**Objetivo:** Uma experiência financeira coesa — sem alterar APIs, backend ou regras.

---

## 1. Situação atual (fragmentada)

```
Financeiro (nav)
├── Receitas          → dashboard.js / financialOverview.js
├── Despesas          → expenses.js / financialExpenses.js
├── Intel. Financeira → financialIntelligence.js
└── Avançado (4 motores)
    ├── Contas a pagar → accountsPayable.js
    ├── Fluxo de caixa → cashFlow.js
    ├── Extratos       → cashOperations.js
    └── Conciliação    → financeCenter.js
```

**Problemas:**
- 7 entradas para o mesmo domínio “dinheiro”
- Receitas e Despesas são duas telas quando o diretor pensa “resultado financeiro”
- Tesouraria espalhada em 4 motores
- Banner resiliência duplicado em Receitas e Despesas

---

## 2. Proposta — Hub Financeiro (UX only)

### Menu Financeiro (3 entradas)

| # | Entrada | Conteúdo | Implementação |
|---|---------|----------|---------------|
| 1 | **Visão Financeira** | Receita · Despesa · Margem · DRE resumido | Hub com **sub-abas internas** Receitas \| Despesas |
| 2 | **Inteligência** | Score · riscos · oportunidades | `financialIntelligence.js` (inalterado) |
| 3 | **Tesouraria** | Fluxo · contas · extratos · conciliação | Hub com **sub-abas internas** |

### Sub-abas — Visão Financeira

| Sub-aba | Render atual | API atual |
|---------|--------------|-----------|
| Receitas | `renderDashboard` | Mesmas calls `dashboard` |
| Despesas | `renderExpenses` | Mesmas calls `expenses` |

**UX:** KPIs consolidados no topo do hub (4 tiles rede); sub-aba troca gráfico/tabela inferior.

### Sub-abas — Tesouraria

| Sub-aba | Render atual |
|---------|--------------|
| Fluxo | `cashFlow.js` |
| Contas | `accountsPayable.js` |
| Extratos | `cashOperations.js` |
| Conciliação | `financeCenter.js` |

---

## 3. Wireframe lógico

```
┌─────────────────────────────────────────┐
│ Visão Financeira    Inteligência  Tesouraria │  ← 3 abas nav
├─────────────────────────────────────────┤
│ [Receita] [Despesa] [Margem] [Alertas]  │  ← KPIs fixos hub
├─────────────────────────────────────────┤
│  Receitas  |  Despesas                  │  ← sub-abas (só no hub 1)
│  ─────────────────────────────────────  │
│  (conteúdo render existente)            │
└─────────────────────────────────────────┘
```

---

## 4. O que NÃO muda

- Endpoints `/api/v1/finance/*`, `/api/v1/dashboard/*`, etc.
- Serviços backend e snapshot-first
- Filtros globais (Período + Empresa)
- Paginação e export CSV por tela

---

## 5. Benefícios

| Antes | Depois |
|-------|--------|
| 7 cliques para explorar financeiro | 3 entradas + 1 sub-aba |
| Diretor não vê margem unificada | KPIs fixos no hub |
| 4 motores “Avançado” | 1 entrada Tesouraria |
| Banner snapshot ×2 | 1 banner no hub ou só Admin |

---

## 6. Plano de implementação

| Passo | Esforço | Remove complexidade? |
|-------|---------|----------------------|
| Criar `financialHub.js` wrapper (sub-nav + KPIs) | M | ✓ |
| Atualizar `navigation.js` (3 entradas) | S | ✓ |
| Redirect aliases `dashboard`/`expenses` → hub | S | ✓ |
| Absorver 4 motores em Tesouraria | M | ✓ |
| Mover banner resiliência p/ detalhe ou Admin | S | ✓ |

---

## 7. Classificação

| Critério | Status |
|----------|--------|
| Consolida sem perda funcional | **APROVADO** |
| Sem API/backend novo | **APROVADO** |
| Reduz telas financeiras 7→3 | **APROVADO** |
| Melhora margem em 5s | **APROVADO** |

---

**IA-3 — Conclusão:** Consolidar financeiro em **Visão + Inteligência + Tesouraria** é a maior alavanca RT-07 para clareza executiva.
