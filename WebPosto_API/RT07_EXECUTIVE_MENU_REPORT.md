# RT-07 — IA-6: Executive Menu Rebuild

**Limite:** ≤3 entradas por macroárea · menu executivo definitivo

---

## 1. Menu atual vs proposto

### Executivo

| Atual (3 abas + 3 motores) | RT-07 proposto (3 abas) |
|----------------------------|-------------------------|
| Resumo | **Resumo** |
| Indicadores | **Indicadores** |
| Alertas | **Alertas** |
| ~~Metas, Comparativo, Visão corporativa~~ | Widgets no Resumo/Indicadores |

### Financeiro

| Atual (3 + 4 motores) | RT-07 proposto (3 abas) |
|-----------------------|-------------------------|
| Receitas | **Visão Financeira** (hub Receitas+Despesas) |
| Despesas | *(absorvida no hub)* |
| Intel. Financeira | **Inteligência** |
| ~~Contas, Fluxo, Extratos, Conciliação~~ | **Tesouraria** (hub 4 sub-abas) |

### Combustíveis

| Atual (3 + 3 motores) | RT-07 proposto (3 abas) |
|-----------------------|-------------------------|
| Vendas | **Vendas** |
| Estoque & Tanques | **Estoque** |
| Governança | **Governança** |
| ~~LMC, Bombas, Visão exec.~~ | Detalhes em Estoque/Vendas |

### Produtos Vendidos

| Atual (3 + 1 motor) | RT-07 proposto (1 aba) |
|---------------------|------------------------|
| Vendas & Mix | **Produtos Vendidos** (hub) |
| Oportunidades | sub-aba |
| Resultados | sub-aba Performance |
| ~~Plano de ações~~ | widget |

*Nota:* Produtos fica com **1 entrada nav** + sub-abas internas — ainda ≤3 cliques cognitivos.

### Fiscal

| Atual | RT-07 |
|-------|-------|
| NFCE | **NFCE** |
| Conciliação | **Conciliação** |
| Tributação & Riscos | **Tributação** |

**Sem alteração** — já ótimo.

### Administração

| Atual (2 + 2 motores) | RT-07 proposto (2 abas) |
|-----------------------|-------------------------|
| Sistema | **Sistema** |
| Diagnóstico Técnico | **Diagnóstico** |
| ~~Operadores, Pessoas~~ | Seções dentro de Sistema |

---

## 2. Menu definitivo RT-07

```
📊 Executivo
   Resumo | Indicadores | Alertas

💰 Financeiro
   Visão Financeira | Inteligência | Tesouraria

⛽ Combustíveis
   Vendas | Estoque | Governança

🛒 Produtos Vendidos
   Produtos Vendidos  (+ sub: Mix | Oportunidades | Performance)

📑 Fiscal
   NFCE | Conciliação | Tributação

⚙️ Administração
   Sistema | Diagnóstico
```

**Total entradas sidebar + abas:** **14** (meta 12–15 ✓)  
**Total experiências (com sub-abas):** **~18** (meta ✓)

---

## 3. Faixa “Avançado” / motor-strip

| Decisão | Motivo |
|---------|--------|
| **Eliminar** `motor-strip` em Executivo, Financeiro, Combustíveis, Produtos | Hubs absorvem |
| **Manter** oculto em Admin se necessário | RH operacional |
| Renomear label se mantido | “Complementos” → evitar “técnico” |

---

## 4. Sidebar — 6 macroáreas (mantém)

Sem novas áreas. Sem novos ícones. Sem “centros” ou “motores” no label.

---

## 5. Deep links / aliases

| Alias antigo | Redirect RT-07 |
|--------------|----------------|
| `dashboard`, `expenses` | `financialHub?view=receitas\|despesas` |
| `cashFlow`, `accounts`, … | `treasuryHub?view=…` |
| `commercialCopilot`, … | `nonFuelProducts?tab=…` |
| `learning`, `recommendations` | `executiveWorkspace` ou 404 amigável |

---

## 6. Classificação

| Critério | Status |
|----------|--------|
| ≤3 entradas/área (nav) | **APROVADO** no desenho |
| 12–15 principais | **14 entradas** ✓ |
| Remove motores visíveis | **APROVADO** |
| Sem funcionalidade nova | **APROVADO** |

---

**IA-6 — Conclusão:** Menu definitivo = **14 entradas · 6 áreas · 0 motor-strip** na camada executiva.
