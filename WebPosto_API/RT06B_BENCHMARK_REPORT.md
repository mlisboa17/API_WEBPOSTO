# RT-06B — Agente 9: Visual Benchmark

**Referências:** SAP Fiori · SAP Analytics Cloud · Power BI Premium · Tableau Executive · Enterprise UX

---

## Matriz — O que copiar

| Padrão | Referência | Aplicação LOGOS SPACE |
|--------|------------|------------------------|
| KPI Hero tiles | SAP Fiori Analytical List Page | `.exec-kpi-tile` — **já aplicado** |
| Date Range Picker popover | Power BI / GA4 | `DateRangePicker` DRP — **já aplicado** |
| Insight cards com severidade | SAC Smart Insights | `.exec-alert-card` — **já aplicado** |
| Sidebar + 3 tabs | Fiori Launchpad groups | `navigationShell` — **já aplicado** |
| Collapsed filters | SAC explorer | `<details>` avançado — **parcial** |
| Single accent color | Fiori Quartz | Verde `#107e3e` — **ok** |
| White space / card elevation | Power BI Premium | `--shadow-soft` — **melhorar** |
| Narrative title + subtitle | Tableau Executive | `periodSubtitle` — **ok** |
| Drill-down in `<details>` | SAC | `executiveInsightDetail` — **ok** |

---

## Matriz — O que evitar

| Anti-padrão | Onde vimos | LOGOS hoje |
|-------------|------------|------------|
| Formulário no topo | ERP legado | Barra filtros acima do conteúdo |
| Banner de sistema | Admin panels | `fin-resilience-banner` em Receitas |
| Bootstrap dashboard | CRUD apps | Reduzido pós RT-06 |
| Múltiplos refresh | Apps internos | 3 botões |
| Tabela como hero | Data grids | Vendas Combustível |
| Labels técnicos | DevOps UI | snapshot, circuit, lineage |
| Inputs de data | ERP forms | Removido ✓ |

---

## Matriz — O que adaptar

| Referência | Adaptação LOGOS |
|------------|-----------------|
| SAP Object Page header | Título + 4 KPIs + período no header da view (não global) |
| Power BI filter pane | Chip “Período · Empresa” colapsável no canto |
| Tableau story points | Brief 4 perguntas só no detalhe |
| Fiori semantic colors | `crit` / `warn` / `ok` nos KPIs — expandir |
| SAC mobile | Stack KPIs 2x2 em mobile — verificar breakpoints |

---

## Paleta e tipografia (target)

| Token | Valor sugerido | Uso |
|-------|----------------|-----|
| `--exec-green` | `#107e3e` | Ação, KPI positivo |
| `--exec-text` | `#32363a` | Títulos SAP-like |
| `--exec-muted` | `#6a6d70` | Subtítulos |
| KPI value | 1.85rem bold | Hero number |
| Card radius | 14px | Premium feel |

---

## Score de proximidade visual

| Referência | Proximidade (0-10) |
|------------|-------------------|
| SAP Fiori | 6 |
| SAP Analytics Cloud | 5 |
| Power BI Premium | 6 |
| Tableau Executive | 5 |
| ERP tradicional | 3 (ainda vaza) |

---

**Agente 9 — Conclusão:** Fundação visual RT-06 **alinhada** com enterprise. Gap principal = **layout shell** e **ruído técnico**, não componentes isolados.
