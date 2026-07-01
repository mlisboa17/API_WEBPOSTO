# RT05 — IA-2: Filter Reduction Audit

**Data:** 2026-06-09 | **Fonte:** `frontend/components/filters.js`, `frontend/app.js` (`filterVisibleFieldsForView`)  
**Meta RT-05 MASTER:** reduzir **60–80%** filtros visíveis · manter somente **Período + Empresa** no default

---

## Inventário completo de filtros

| # | Campo | Label UI | Telas visíveis | Uso observado (RT-04) | Classificação |
|---|---|---|---|---|---|
| 1 | dataInicial | Data inicial | **Todas (18)** | Diário | **Executivo** |
| 2 | dataFinal | Data final | **Todas (18)** | Diário | **Executivo** |
| 3 | empresaCodigo | Empresa | **Todas (18)** | Diário/semanal | **Executivo** |
| 4 | centroCusto | Centro de custo | **Todas (18)** | Raro (fechamento) | **Operacional** |
| 5 | tipoDespesa | Tipo despesa | **Todas (18)** | Raro | **Operacional** |
| 6 | texto | Texto | **Todas (18)** | Esporádico (auditoria) | **Operacional** |
| 7 | valorMin | Valor mínimo | **Todas (18)** | Raro | **Operacional** |
| 8 | valorMax | Valor máximo | **Todas (18)** | Raro | **Operacional** |
| 9 | expenseNature | Natureza | Despesas | Semanal (financeiro) | **Operacional** |
| 10 | expenseManagementGroup | Grupo Gerencial | Despesas | Raro | **Técnico** |
| 11 | expenseManagementClass | Classe Gerencial | Despesas | Raro | **Técnico** |
| 12 | dreImpact | Impacta DRE | Despesas | Raro | **Técnico** |
| 13 | cashFlowImpact | Impacta Caixa | Despesas | Raro | **Técnico** |
| 14 | origem | Origem (financeiro/caixa/pdv) | Despesas | Esporádico | **Técnico** |

**Filtros internos de tabela** (não no painel global, mas visíveis na 1ª dobra em Receitas/Despesas/Vendas/Estoque): busca por coluna, ordenação, paginação — **+3–8 controles por tabela**.

---

## Uso diário vs raro vs técnico

| Categoria | Filtros | Qtd |
|---|---|---|
| **Uso diário** | dataInicial, dataFinal, empresaCodigo | **3** |
| **Uso semanal/raro** | centroCusto, tipoDespesa, texto, valorMin, valorMax, origem, natureza | **7** |
| **Técnico/contábil** | grupo gerencial, classe gerencial, impacta DRE, impacta caixa | **4** |

---

## Proposta de redução (sem remover funcionalidade)

### Padrão executivo MASTER (todas as 18 telas RT-01)

| Estado | Visível | Oculto em “Filtros Avançados” |
|---|---|---|
| **Antes** | 8 filtros | — |
| **Depois** | **2 filtros** (dataInicial + dataFinal como **Período** · empresaCodigo) | 6 filtros |
| **Redução** | **75%** | ✅ Meta 60–80% |

### Despesas (auditoria financeira)

| Estado | Visível | Oculto em painel avançado |
|---|---|---|
| **Antes** | 13 filtros | — |
| **Depois** | **2 filtros** + botão “Filtros avançados” | 11 filtros |
| **Redução** | **84,6%** | ✅ Meta superada |

### Filtros de tabela

| Ação | Telas |
|---|---|
| Manter busca global da tabela | Despesas, Vendas, Estoque |
| Ocultar filtros por coluna até drill-down | Receitas, Despesas |
| Export/PDF | Mover para menu “⋯” | Todas com tabela |

---

## Filtros que devem ficar ocultos por perfil

| Perfil | Ocultar do default |
|---|---|
| **Diretoria** | Todos exceto período + empresa (10–11 campos) |
| **Financeiro operacional** | Período + empresa + natureza visíveis; resto avançado |
| **Operação/Comercial/Fiscal** | Período + empresa; demais avançado |
| **Administrador** | Manter avançado acessível, não default |

---

## Impacto esperado

```text
Chrome de filtros hoje:     ~280px altura (8 campos em grid)
Chrome proposto:            ~80px  (3 campos + link "Avançado")
Espaço vertical recuperado: ~200px por tela (= 1ª dobra de KPIs)
```

---

## Respostas IA-2

| Pergunta | Resposta |
|---|---|
| Quantos filtros podem ser ocultados? | **11 de 13** (Despesas) · **6 de 8** (demais telas) |
| Quantos devem virar painel avançado? | **11 campos** + filtros de coluna |
| Meta 60–80% atingida? | **Sim** — 75% (geral) · 84,6% (Despesas) |
| Visíveis default MASTER | **Somente Período + Empresa** |

---

**[IA-2 APROVADA — plano de redução de filtros ≥60% documentado]**
