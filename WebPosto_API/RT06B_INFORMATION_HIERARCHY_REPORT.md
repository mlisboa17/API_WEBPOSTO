# RT-06B — Agente 2: Information Hierarchy

**Regra oficial:** NEGÓCIO → KPI → ALERTA → AÇÃO → DETALHE → FILTROS

---

## Shell global

| Ordem atual (`index.html`) | Ordem SAP-FIRST |
|----------------------------|-----------------|
| 1. Topbar | 1. Topbar |
| 2. **Filtros** | 2. Sidebar + Abas |
| 3. Abas | 3. **Título + KPIs + Gráfico + Alertas** |
| 4. Motor strip | 4. Detalhamento |
| 5. Conteúdo | 5. **Filtros (colapsados)** |

**Classificação shell:** **REPROVADA**

---

## Telas prioritárias

| Tela | Diretor vê Receita/Despesa/Margem/Alertas em 5s? | Filtros antes do negócio? | Classificação |
|------|---------------------------------------------------|---------------------------|---------------|
| Resumo Executivo | Sim — 4 KPIs + alertas | Sim (shell) | **PARCIAL** |
| Alertas | Parcial — foco em alertas, KPIs genéricos | Sim (shell) | **PARCIAL** |
| Receitas | Sim, após banner técnico | Sim (shell) | **PARCIAL** |
| Despesas | Sim, após banner técnico | Sim (shell) | **PARCIAL** |
| Intel. Financeira | Parcial — “Margem” = score | Sim (shell) | **PARCIAL** |
| Produtos Vendidos | Sim — mix/Pareto | Sim (shell) | **PARCIAL** |
| Vendas Combustível | Não — KPIs “—” | Sim (shell) | **REPROVADA** |
| NFCE | Parcial — emitidas/canceladas | Sim (shell) | **PARCIAL** |
| Conciliação Fiscal | Sim — cobertura fiscal | Sim (shell) | **PARCIAL** |

**Resumo:** 0 APROVADA · 7 PARCIAL · 1 REPROVADA

---

## Tempo para entendimento (estimativa)

| Tela | Segundos até insight | Bloqueio |
|------|---------------------|----------|
| Resumo Executivo | ~3s | Filtros competem atenção |
| Receitas | ~6s | Banner resiliência |
| Despesas | ~6s | Banner + filtros avançados visíveis ao expandir |
| Vendas Combustível | >8s | KPIs vazios |

---

## Ações P0

1. Reordenar DOM: conteúdo antes de filtros (ou filtros sticky recolhidos)
2. Remover banner resiliência da 1ª dobra em Receitas/Despesas
3. Corrigir hierarquia semântica em `sales.js` e `nfceIntelligence.js`
4. Garantir 4 KPIs de negócio legíveis sem scroll em mobile

---

**Agente 2 — Conclusão:** Informação executiva **existe**, mas **não aparece primeiro**. Hierarquia SAP-FIRST = **NÃO ATENDIDA** no layout global.
