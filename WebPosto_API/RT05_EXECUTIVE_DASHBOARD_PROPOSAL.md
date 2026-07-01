# RT05 — IA-7: Executive Dashboard Proposal

**Data:** 2026-06-09 | **Status:** especificação conceitual **sem implementação**  
**Referências:** SAP Fiori Overview Page · SAP Smart Business · Power BI Premium mobile executive

---

## Princípio

Uma única **Overview Executiva** substitui a leitura fragmentada de Resumo + Indicadores + parte de Alertas — **sem API nova**, apenas reorganização de dados já consumidos pelo `executiveWorkspace` e cockpits RT-01.

---

## Layout proposto — wireframe textual

### 1ª dobra (decisão em 5 segundos)

```text
┌──────────────────────────────────────────────────────────────────┐
│ LOGOS SPACE                              [Período ▼] [Empresa ▼] │
│ Visão executiva · 01/06/2026 → 07/06/2026                      │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ RECEITA  │ │ DESPESA  │ │ MARGEM   │ │ ALERTAS  │          │
│  │ R$ …     │ │ R$ …     │ │ R$ …     │ │ 3 crít.  │          │
│  │ ▲ vs ant │ │ ▼ vs ant │ │ ● stable │ │ [ver →]  │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│                                                                  │
│  ┌──────────────────────── GRÁFICO PRINCIPAL ──────────────────┐ │
│  │  Receita vs Despesa · últimos 7 dias (barras empilhadas)    │ │
│  │  ou sparkline de margem consolidada                         │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ALERTAS PRIORITÁRIOS (máx. 3)                                  │
│  🔴 LMC atrasado — Posto X                    [Agir →]          │
│  🟠 NFCE pendente — Filial Y                  [Agir →]          │
│  🟠 Despesa acima meta — Centro Z            [Agir →]          │
└──────────────────────────────────────────────────────────────────┘
```

**Componentes SAP equivalentes:** KPI Header (4 tiles) · Chart Container · Notification List (3 items)

---

### 2ª dobra (contexto)

```text
┌──────────────────────────────────────────────────────────────────┐
│ OPORTUNIDADES (top 5)              │ FILIAIS EM RISCO (top 5)   │
│ tabela compacta                    │ lista com semáforo          │
├────────────────────────────────────┴────────────────────────────┤
│ ATALHOS DE DECISÃO                                               │
│ [Receitas] [Despesas] [NFCE] [Vendas] [Estoque]                 │
└──────────────────────────────────────────────────────────────────┘
```

---

### 3ª dobra (detalhamento / drill-down)

```text
┌──────────────────────────────────────────────────────────────────┐
│ Execução de ações · Desempenho por filial · Rankings             │
│ (conteúdo atual dos blocos 3–5 do executiveWorkspace)            │
└──────────────────────────────────────────────────────────────────┘
```

---

### Filtros avançados (painel recolhível)

```text
[ ▼ Filtros avançados ]  ← collapsed por default

Quando expandido:
  Centro de custo · Tipo despesa · Texto · Valor min/max
  Natureza · Grupo/Classe gerencial · Impacta DRE/Caixa · Origem

Botões: [Aplicar] [Limpar]
```

**Padrão Fiori:** Filter Bar com "Adapt Filters" dialog.

---

## Mapeamento dados existentes → layout (sem API nova)

| Tile proposto | Fonte atual |
|---|---|
| Receita | `workspaceEngine` → scorecard.faturamento / overview |
| Despesa | overview.consolidado.total_despesas |
| Margem | commercialExecution / nonFuelProducts |
| Alertas | actionCenter.prioridade1.length + fuelGovernance |
| Gráfico | overview por dia (derivar de despesas/receitas já carregadas) ou sparkline scorecard |
| 3 alertas | workspace.alerts.slice(0,3) |
| Oportunidades | workspace.opportunities |

---

## Perfil Diretoria vs Operação

| Elemento | Diretoria | Operação/Financeiro |
|---|---|---|
| Filtros default | Período + Empresa | + Natureza (financeiro) |
| Strip Avançado | **Oculto** | Visível |
| F08.3 Diagnóstico | **Oculto** | Admin only |
| KPIs ROI técnico | **Oculto** | Avançado |
| Lineage | **Oculto** | Avançado |

---

## Navegação proposta (pós RT-05 UX)

```text
Sidebar (4 áreas para diretoria):
  📊 Visão Geral      → Overview executiva (nova organização do Resumo)
  💰 Financeiro       → Receitas | Despesas | Inteligência (3 abas)
  ⛽ Operação          → Combustíveis + Fiscal (submenu compacto)
  ⚙️ Administração    → TI only

Motores F03–F07: 100% em "Avançado" ou Admin — zero na sidebar diretoria.
```

---

## Critérios de aceite da proposta

| Critério | Atendido? |
|---|---|
| Responde "o que aconteceu?" | ✅ KPIs + gráfico |
| "Existe problema?" | ✅ 3 alertas |
| "Preciso agir?" | ✅ CTA em alertas |
| "Onde agir?" | ✅ links para telas RT-01 |
| Leitura < 5 segundos | ✅ 1ª dobra ≤ 12 elementos |
| Sem API nova | ✅ recombinar payloads existentes |
| SAP Fiori aligned | ✅ Overview Page pattern |

---

## Fases de implementação futura (fora RT-05)

| Fase | Escopo | Sprint |
|---|---|---|
| RT-05 | Auditoria + spec (esta entrega) | RT-05 ✅ |
| RT-06 | Collapse filtros + 4 KPIs | UX only |
| RT-07 | Overview layout + gráfico hero | UX only |
| RT-08 | Perfil Diretoria (hide motors) | UX only |

---

**[IA-7 APROVADA — proposta executiva SAP/Fiori documentada]**
