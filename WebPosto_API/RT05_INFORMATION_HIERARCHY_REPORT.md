# RT05 — IA-3: Executive Information Hierarchy

**Data:** 2026-06-09 | **Regra obrigatória:** 1ª dobra = título + 4 KPIs + 1 gráfico + 3 alertas prioritários

---

## Padrão alvo (SAP Fiori / Smart Business)

```text
┌─────────────────────────────────────────────┐
│ Título + período + empresa          [⋯]    │  ← 1ª dobra
│ [KPI1] [KPI2] [KPI3] [KPI4]              │
│ [══════════ Gráfico principal ══════════] │
│ ⚠ Alerta 1  ⚠ Alerta 2  ⚠ Alerta 3        │
├─────────────────────────────────────────────┤
│ Detalhamento / tabelas / drill-down        │  ← 2ª dobra
├─────────────────────────────────────────────┤
│ Motores · lineage · export · técnico       │  ← 3ª dobra / Avançado
└─────────────────────────────────────────────┘
```

---

## Auditoria 1ª dobra — 18 telas RT-01

| Tela | Título OK | 4 KPIs max | 1 gráfico | 3 alertas | **Conforme?** | Problema principal |
|---|---|---|---|---|---|---|
| Resumo Executivo | ✅ | ❌ (6 cards) | ❌ | ⚠️ (até 8) | **NÃO** | 5 blocos na 1ª dobra |
| Indicadores | ✅ | ❌ (8 KPIs) | ❌ | ❌ | **NÃO** | JSON tendências visível |
| Alertas | ✅ | ❌ (8 KPIs) | ❌ | ❌ (tabelas) | **NÃO** | KPIs de ROI antes dos alertas |
| Receitas | ⚠️ | ⚠️ (3 KPIs) | ❌ | ❌ | **PARCIAL** | Tabela compete com cards |
| Despesas | ⚠️ | ❌ (0 KPIs) | ❌ | ❌ | **NÃO** | 13 filtros ocupam 1ª dobra |
| Intel. Financeira | ✅ | ❌ (~12) | ❌ | ❌ | **NÃO** | 6 seções empilhadas |
| F08.3 Diagnóstico | ✅ | ❌ (13+) | ❌ | ⚠️ | **NÃO** | Painel TI, não executivo |
| Produtos Performance | ✅ | ❌ (7) | ❌ | ❌ | **NÃO** | 6 tabelas na dobra |
| Oportunidades | ✅ | ⚠️ | ❌ | ❌ | **NÃO** | Copiloto domina |
| Ações Comerciais | ✅ | ❌ | ❌ | ❌ | **NÃO** | Motor F07 |
| Resultados | ✅ | ❌ | ❌ | ❌ | **NÃO** | Calibração/ROI técnico |
| Vendas | ⚠️ | ✅ (0 KPI) | ⚠️ (tabela) | ❌ | **PARCIAL** | Subtabs + filtros globais |
| Estoque | ⚠️ | ✅ | ⚠️ | ❌ | **PARCIAL** | Filtros globais |
| LMC | ✅ | ❌ | ❌ | ❌ | **NÃO** | Engines de reconciliação |
| Governança | ✅ | ❌ | ❌ | ⚠️ | **NÃO** | KPIs de conformidade dispersos |
| NFCE | ✅ | ❌ | ❌ | ❌ | **NÃO** | Risk engine + patterns |
| Conciliação Fiscal | ✅ | ⚠️ | ❌ | ❌ | **NÃO** | Lineage na 1ª dobra |
| Tributação | ✅ | ⚠️ | ❌ | ❌ | **NÃO** | taxClassificationEngine |

**Conformidade global:** **0 / 18** telas atendem a regra completa · **3 parciais** · **15 reprovadas**

---

## O que mover para 2ª / 3ª dobra

| Tela | Manter na 1ª dobra | Mover para 2ª dobra | Mover para 3ª / Avançado |
|---|---|---|---|
| Resumo Executivo | 4 KPIs rede + 3 alertas | Oportunidades (tabela) | Execução ROI, 5 rankings filial |
| Alertas | 3 alertas P1 + contador | Tabelas P1/vencidas | KPIs ROI, rastreabilidade |
| Indicadores | 4 scores principais | Top filiais/operadores | JSON tendências, paridade Δ |
| Receitas | 4 KPIs financeiros | Gráfico receita/despesa | Tabela por posto |
| Despesas | 4 KPIs totais (novo) | Tabela despesas | Filtros avançados |
| Intel. Financeira | Score + 4 riscos top | Tendências | Fluxo, recebíveis/pagáveis |
| Produtos | 4 KPIs mix/margem | 1 tabela pareto | Demais 5 tabelas |
| NFCE/Fiscal | 4 KPIs conformidade | 1 tabela pendências | Engines, lineage |

---

## Hierarquia recomendada — 4 KPIs universais

Para telas executivas, padronizar:

| KPI | Origem |
|---|---|
| **Receita** | Scorecard / overview |
| **Despesa** | Overview / despesas |
| **Margem** | Comercial / overview |
| **Alertas** | Action center (contagem P1) |

Substituir KPIs técnicos (ROI Δ, R04 gate, paridade Δ, calibradas) por **indicadores de negócio**.

---

## Chrome que compete com a 1ª dobra

| Elemento | Altura estimada | Ação |
|---|---|---|
| Barra de 8 filtros | ~280px | Recolher → 3 campos |
| Sidebar + abas + motores | ~120px vertical mental | OK lateral; motores só 2ª interação |
| Topbar LOGOS SPACE | ~80px | Reduzir subtítulo em telas internas |

---

**[IA-3 APROVADA — hierarquia auditada; 0/18 conformes hoje]**
