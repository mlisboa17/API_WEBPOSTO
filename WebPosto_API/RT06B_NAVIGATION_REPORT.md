# RT-06B — Agente 7: Navigation Rebuild

**Macroáreas oficiais:** Executivo · Financeiro · Combustíveis · Produtos Vendidos · Fiscal · Administração  
**Limite:** 3 telas principais por macroárea

---

## Mapa atual (`config/navigation.js`)

| Macroárea | Abas principais (≤3) | Avançado (motor strip) | Total navegável |
|-----------|----------------------|------------------------|-----------------|
| **Executivo** | Resumo, Indicadores, Alertas | Metas, Comparativo, Visão corporativa | 6 |
| **Financeiro** | Receitas, Despesas, Intel. Financeira | Contas, Fluxo, Extratos, Conciliação | 7 |
| **Combustíveis** | Vendas, Estoque, Governança | LMC, Bombas, Visão exec. combustível | 6 |
| **Produtos Vendidos** | Vendas & Mix, Oportunidades, Resultados | Plano de ações | 4 |
| **Fiscal** | NFCE, Conciliação, Tributação | — | 3 |
| **Administração** | Sistema, Diagnóstico Técnico | Operadores, Pessoas | 4 |

**Regra 3 abas:** **ATENDIDA** em todas as macroáreas ✓

---

## Classificação por item

### MANTER (telas principais)
- Resumo Executivo, Alertas, Receitas, Despesas, Intel. Financeira
- Vendas Combustível, Estoque, NFCE, Conciliação
- Administração / Diagnóstico Técnico

### UNIFICAR (candidatos)
| De | Para | Motivo |
|----|------|--------|
| Indicadores + Resumo | Resumo (tabs internas) | Sobreposição executiva |
| Fluxo + Extratos + Conciliação | “Tesouraria” (motor único) | 4 motores financeiros |
| LMC + Bombas + Visão exec. | “Operações combustível” | Reduzir fragmentação |
| Oportunidades + Resultados | “Comercial” sub-nav | 2 telas copilot/learning similares |

### OCULTAR (já parcialmente ocultos)
| View | Status |
|------|--------|
| `executive` (legado) | No DOM, fora da nav — **remover** |
| `financialMonitoring` | Redireciona p/ Diagnóstico ✓ |
| `financialOperations` | Redireciona p/ Diagnóstico ✓ |
| `learning`, `recommendations`, `executiveCopilot` | Motores / áreas secundárias |

---

## Views órfãs / redundantes

| View | Arquivo | Na nav? |
|------|---------|---------|
| `executive` | `executiveDashboard.js` | Não |
| `executiveWorkspace` | `executiveWorkspace.js` | Sim (Resumo) |
| `dashboard` | `dashboard.js` via `financialOverview.js` | Sim (Receitas) |
| `expenses` | `expenses.js` via `financialExpenses.js` | Sim (Despesas) |

---

## Recomendações

1. **P0:** Remover view legada `executive` do DOM e roteamento
2. **P1:** Renomear motor strip “Avançado” → “Módulos complementares” (menos técnico)
3. **P2:** Consolidar motores financeiros (UX nav only, sem merge de APIs)

---

## Classificação

| Critério | Status |
|----------|--------|
| 6 macroáreas | **APROVADO** |
| ≤3 abas/área | **APROVADO** |
| Telas técnicas em Admin | **APROVADO** |
| Fragmentação motores | **PARCIAL** |

---

**Agente 7 — Conclusão:** Navegação **estruturalmente correta** (RT-03B). Refino de **unificação** recomendado, não bloqueador.
