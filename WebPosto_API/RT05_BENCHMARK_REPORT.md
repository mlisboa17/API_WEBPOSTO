# RT05 — Benchmark Report

**Data:** 2026-06-09 | **Referências:** SAP Fiori · SAP Analytics Cloud · Power BI Premium · Tableau Enterprise · Looker · padrões Dribbble/Behance executive dashboard  
**Escopo:** 18 telas RT-01 vs padrão enterprise

---

## 1. Framework de avaliação

| Dimensão | Peso | Descrição |
|---|---:|---|
| Hierarquia visual | 25% | KPIs antes de filtros/tabelas |
| Densidade informação | 25% | Elementos na 1ª dobra (meta ≤12) |
| Leitura 5 segundos | 25% | 4 perguntas executivas respondidas |
| Estética enterprise | 15% | Whitespace · semáforo · não-bootstrap |
| Drill-down | 10% | Overview → detail pattern |

**Escala:** 0–10 por dimensão · **Aprovado enterprise:** ≥7,0 · **Mediocre:** <5,0

---

## 2. Padrões de referência

### SAP Fiori — Overview Page

```text
• 4 KPI tiles (Analytical Card)
• 1 chart container
• Notification list (3–5 items)
• Filter bar adaptativo (collapsed)
• Semantic colors: Good / Critical / Neutral
```

**Fonte:** SAP Fiori Design Guidelines — Overview Page pattern.

### SAP Analytics Cloud — Story

```text
• Single hero visual per canvas
• Responsive reflow
• Linked analysis (drill, not parallel tables)
```

### Power BI Premium — Executive mobile

```text
• 4 cards above fold on phone
• Single primary visual
• Bookmarks per persona
```

### Tableau Executive

```text
• One story per decision
• Color sparingly (3-state semaphore)
• Minimal chrome
```

### Looker Enterprise

```text
• Clean dashboard layer
• Explore hidden from executives
• Consistent KPI definitions
```

### Dribbble / Behance (padrões recorrentes 2024–2026)

```text
• Dark-on-light ou light minimal
• 4 metric cards top row
• Large hero chart center
• Rounded cards 12–16px radius
• 40%+ whitespace
• No filter grid above metrics
```

---

## 3. Scorecard LOGOS SPACE vs enterprise

| Tela | Hier. | Dens. | 5s | Estét. | Drill | **Total** | vs ERP BR | vs SAP |
|---|---:|---:|---:|---:|---:|---:|---|---|
| Vendas | 8 | 8 | 7 | 7 | 8 | **7,6** | Acima | Próximo |
| Estoque | 7 | 7 | 6 | 7 | 7 | **6,8** | Acima | Médio |
| Receitas | 7 | 6 | 6 | 6 | 7 | **6,4** | Médio | Médio |
| Conciliação Fiscal | 7 | 6 | 5 | 6 | 6 | **6,0** | Médio | Médio |
| Resumo Executivo | 7 | 5 | 5 | 7 | 6 | **6,0** | Médio | Médio |
| NFCE / Governança / Trib. | 6 | 5 | 4 | 5 | 5 | **5,0** | Médio | Distante |
| Alertas / Intel. Fin. | 6 | 4 | 4 | 5 | 5 | **4,8** | Abaixo | Distante |
| Despesas / Indicadores | 4 | 3 | 3 | 4 | 6 | **4,0** | Abaixo | Distante |
| Produtos / Resultados | 4 | 3 | 3 | 3 | 4 | **3,4** | Abaixo | Distante |
| F08.3 Diagnóstico | 3 | 2 | 1 | 3 | 5 | **2,8** | N/A TI | N/A |

**Média LOGOS:** **5,4 / 10**  
**Média ERP postos BR (heurística mercado):** ~4,5/10  
**Meta SAP-aligned:** ≥7,5/10

---

## 4. Posicionamento competitivo

```text
                    DENSO ←────────────────→ LIMPO
                         │
    ERP postos BR ───────┼─── LOGOS hoje
                         │
                         │        ═══ META RT-06 (Overview)
                         │
                         └──── SAP Fiori / PBI Premium
```

| Comparativo | LOGOS hoje | Meta RT-06+ |
|---|---|---|
| vs ERP postos BR | **Acima** (+0,9) | **Muito acima** |
| vs SAP Fiori | **Abaixo** (−2,1) | **Próximo** (−0,5 alvo) |
| vs Power BI Premium | **Abaixo** | **Comparable** |
| vs Tableau Executive | **Abaixo** | **Comparable** |

---

## 5. Gaps críticos vs benchmark

| # | Gap | Referência | Fix UX (RT-06+) |
|---|---|---|---|
| G1 | Filtros acima KPIs | Fiori Filter Bar collapsed | Header inline 2 campos |
| G2 | 6–8 KPIs simultâneos | Fiori max 4 tiles | Consolidar 4 padrão |
| G3 | Sem gráfico hero | SAC / PBI | 1 chart 8-col |
| G4 | Engines visíveis | Looker (explore hidden) | Rename + 3ª dobra |
| G5 | Strip Avançado | — (anti-pattern) | Perfil diretoria hide |
| G6 | JSON debug UI | — (anti-pattern) | Remover Indicadores |
| G7 | Bootstrap table first | Tableau story | Drill-down |
| G8 | Palette inconsistente | Semáforo `#107e3e/#f0ab00/#bb0000` | Tokens CSS |

---

## 6. Cláusula anti-mediocridade — checklist

| Parece… | LOGOS hoje? | Ação |
|---|---|---|
| ERP antigo | ⚠️ Sim (filtros grid) | Collapse filtros |
| Dashboard bootstrap | ⚠️ Parcial (tabelas) | Hero chart |
| Sistema administrativo | ⚠️ F08.3, Despesas | Perfil + hierarquia |
| Tela cheia filtros | ❌ **Sim** | **REPROVADO** |
| Tela cheia tabelas | ❌ Produtos | **REPROVADO** |
| Painel genérico | ⚠️ Indicadores | Unificar Resumo |

---

## 7. Referências visuais recomendadas (implementação RT-06)

| Pattern | Onde aplicar |
|---|---|
| SAP Fiori Analytical Card | 4 KPI tiles |
| SAP Smart Business drill | Tabelas → modal/aba |
| PBI card accent | Left border semáforo |
| Tableau story flow | Overview → detail |
| Dribbble "executive dashboard minimal" | Whitespace + 12-col |

---

## 8. Veredicto benchmark

```text
HOJE:     Funcional · abaixo SAP · acima ERP postos
META:     Comparable PBI/Tableau · próximo SAP Fiori
BLOQUEIO: Filtros + densidade + ruído técnico — não backend
```

---

**[RT05 BENCHMARK — APROVADO]**
