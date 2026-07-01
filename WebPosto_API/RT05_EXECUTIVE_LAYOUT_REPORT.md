# RT05 — Executive Layout Report

**Data:** 2026-06-09 | **Referências:** SAP Fiori Overview · SAP Smart Business · Power BI Premium · Tableau Executive · Looker  
**Status:** especificação visual — **sem implementação**

---

## 1. Design tokens obrigatórios

### Paleta semáforo enterprise

| Token | Hex | Uso |
|---|---|---|
| `--exec-green` | `#107e3e` | OK · meta atingida · tendência positiva |
| `--exec-yellow` | `#f0ab00` | Atenção · risco moderado · prazo próximo |
| `--exec-red` | `#bb0000` | Crítico · ação imediata · meta violada |
| `--exec-bg` | `#f7f7f7` | Fundo página (whitespace) |
| `--exec-surface` | `#ffffff` | Cards e painéis |
| `--exec-text` | `#32363a` | Texto principal (SAP Horizon-like) |
| `--exec-muted` | `#6a6d70` | Subtítulos · hints |

### Tipografia

| Nível | Tamanho | Peso | Uso |
|---|---|---|---|
| H1 página | 24px | 600 | Título da view |
| H2 seção | 18px | 600 | 2ª dobra |
| KPI valor | 28px | 700 | Tile principal |
| KPI label | 12px | 500 | Uppercase tracking |
| Corpo | 14px | 400 | Alertas · tabelas |

---

## 2. Grid system — 12 colunas

```text
┌──1──2──3──4──5──6──7──8──9──10─11─12─┐
│ gutter: 16px · max-width: 1440px      │
│ col-span KPI: 3+3+3+3 = 4 tiles       │
│ col-span chart: 8 (hero) + 4 (side)   │
│ col-span alert: 12 (lista horizontal) │
└───────────────────────────────────────┘
```

| Breakpoint | Colunas | Comportamento |
|---|---|---|
| ≥1280px | 12 | Layout executivo completo |
| 960–1279px | 12 | KPIs 6+6 · chart full |
| <960px | 4 | Stack vertical (mobile executive) |

**Regra:** nunca mais de **12 unidades de informação** na 1ª dobra viewport 1080p.

---

## 3. Componentes — padrão Fiori

### 3.1 Header executivo (col 1–12)

```text
┌────────────────────────────────────────────────────────────┐
│ [Logo compacto]  Visão Executiva                           │
│                  01/06/2026 → 07/06/2026 · Rede consolidada│
│                                    [Período ▼] [Empresa ▼] │
└────────────────────────────────────────────────────────────┘
```

- Subtítulo LOGOS SPACE global **oculto** em views internas (recupera ~40px).
- Período + Empresa = **únicos filtros inline** no header.

### 3.2 KPI tiles (4 × col-span-3)

```text
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ RECEITA     │ │ DESPESA     │ │ MARGEM      │ │ ALERTAS     │
│ R$ 2,4 mi   │ │ R$ 890 mil  │ │ R$ 1,5 mi   │ │ 3 críticos  │
│ ▲ 4,2%      │ │ ▼ 1,1%      │ │ ● estável   │ │ [ver →]     │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

| Propriedade | Valor |
|---|---|
| Border-radius | `12px` |
| Shadow | `0 1px 3px rgba(0,0,0,.08)` (pouca sombra) |
| Padding | `20px 24px` |
| Accent bar | 4px left border (verde/amarelo/vermelho) |

**Proibido na 1ª dobra:** KPIs técnicos (ROI Δ, R04, calibradas, paridade).

### 3.3 Gráfico hero (col 1–8)

```text
┌──────────────────────────────────────────┐
│ Receita vs Despesa · período             │
│ ████ barras empilhadas ou linha dual     │
│                                          │
└──────────────────────────────────────────┘
```

- **1 gráfico** — nunca 2 competindo.
- Dados: overview consolidado + série diária (payload existente RT-02).
- Estilo: Power BI Premium — fundo branco, grid sutil, legenda compacta.

### 3.4 Side panel (col 9–12) — opcional

Mini-ranking top 3 filiais ou sparkline margem — **substituível por gráfico full-width**.

### 3.5 Alertas prioritários (col 1–12, max 3)

```text
┌─ 🔴 ─ LMC atrasado — Posto VIP · 3 dias ──────────── [Agir →] ─┐
├─ 🟡 ─ NFCE pendente — Filial X ──────────────────── [Agir →] ─┤
└─ 🟡 ─ Despesa acima meta — Centro ADMIN ─────────── [Agir →] ─┘
```

| Severidade | Cor | Icon |
|---|---|---|
| Crítico | `#bb0000` | círculo sólido |
| Atenção | `#f0ab00` | triângulo |
| Info | `#107e3e` | apenas 2ª dobra |

---

## 4. Segunda dobra — detalhamento

```text
┌─────────────────────────────┬─────────────────────────────┐
│ Oportunidades (top 5)       │ Filiais em risco (top 5)    │
│ tabela compacta 5 colunas   │ lista semáforo              │
├─────────────────────────────┴─────────────────────────────┤
│ Atalhos: [Receitas] [Despesas] [NFCE] [Vendas] [Estoque] │
└───────────────────────────────────────────────────────────┘
```

---

## 5. Terceira dobra — avançado

```text
[ ▼ Filtros avançados ]     ← collapsed default

Execução · Rankings filial · Export · Lineage (somente financeiro auditor)
```

---

## 6. Anti-patterns — REPROVAR

| Pattern | Por que reprova |
|---|---|
| 8 filtros em grid acima dos KPIs | ERP antigo · viola hierarquia |
| Tabela full-width na 1ª dobra | Dashboard bootstrap |
| JSON / `<pre>` visível | Sistema administrativo |
| 6+ KPIs em fila | Painel genérico |
| Strip "Avançado" visível p/ diretoria | Ruído cognitivo |
| Cards com sombra pesada | Fora padrão Fiori/Horizon |

---

## 7. Mapeamento CSS atual → alvo (RT-06+)

| Classe atual | Ação |
|---|---|
| `.filters` (grid 8 campos) | Collapse → header inline 2 campos |
| `.kpi-card` | Padronizar 4 tiles + accent bar |
| `.ws-summary-grid` (6 cards) | Reduzir → 4 KPIs |
| `.motor-strip` | `display:none` perfil diretoria |
| `.topbar h1 + p longo` | Compactar header |
| `.state.error` boot | Manter (diagnóstico) |

Arquivo alvo: `frontend/styles.css` + tokens em `:root`.

---

## 8. Wireframe ASCII — Overview completa

```text
┌─12 col───────────────────────────────────────────────────────┐
│ HEADER                                    [Período] [Empresa]│
├───────┬───────┬───────┬───────┬──────────────────────────────┤
│ REC   │ DESP  │ MARG  │ ALRT  │                              │
│ 3col  │ 3col  │ 3col  │ 3col  │                              │
├───────┴───────┴───────┴───────┤  CHART HERO (8 col)          │
│ ALERT 1                       │                              │
│ ALERT 2                       ├──────── SIDEBAR (4 col) ──────┤
│ ALERT 3                       │  top filiais / mini KPI      │
├───────────────────────────────┴──────────────────────────────┤
│ 2ª DOBRA: oportunidades · risco · atalhos                    │
├──────────────────────────────────────────────────────────────┤
│ 3ª DOBRA: [filtros avançados ▼] · tabelas · export           │
└──────────────────────────────────────────────────────────────┘
```

---

## 9. Critérios de aceite layout

| Critério | Meta |
|---|---|
| KPIs visíveis antes de filtros | ✅ |
| Máx 4 KPIs 1ª dobra | ✅ |
| 1 gráfico hero | ✅ |
| 3 alertas max | ✅ |
| Palette semáforo | ✅ `#107e3e` `#f0ab00` `#bb0000` |
| Grid 12 col | ✅ |
| Whitespace ≥30% viewport | ✅ |
| Parece SAP/PBI, não bootstrap | ✅ |

---

**[RT05 EXECUTIVE LAYOUT — ESPECIFICAÇÃO APROVADA]**
