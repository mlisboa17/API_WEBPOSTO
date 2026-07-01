# RT01B — Matriz de Corte de Telas (Antirredundância)

**Data:** 2026-06-09 | **Input:** RT-00 + RT01B_EXECUTIVE_SCREEN_INVENTORY.md

---

## Resumo de corte

| Ação | Qtd | IDs |
|---|---|---|
| **Manter** (tela principal) | 18 | 001–003, 005–007, 011–012, 015, 019–021, 025–027, 028* |
| **Unificar** (aba/widget) | 12 | 004, 008–010, 022–024, 027, 034, 005+029 |
| **Eliminar** (navegação) | 2 | 013, 014 |
| **Ocultar** (diretoria) | 8 | 018, 029–040 (exc. unificados) |
| **Corrigir antes** RT-01 | 8 | 005, 016, 017, 028, 006*, 015*, 007, 021* |

\* Já parcialmente validados; manter na RT-01 com ressalva.

---

## Matriz de decisão por tela

| ID | View | Decisão | Destino final | RT-01 |
|---|---|---|---|---|
| TELA-001 | executive-workspace | Manter | Executivo › Resumo | Sim |
| TELA-002 | executive-scorecard | Manter | Executivo › Indicadores | Sim |
| TELA-003 | action-center | Manter | Executivo › Alertas | Sim |
| TELA-004 | goals-campaigns | Unificar | Executivo › aba Metas | Condicional |
| TELA-005 | dashboard | Corrigir antes | Financeiro › Receitas | Sim (live) |
| TELA-006 | expenses | Manter | Financeiro › Despesas | Sim |
| TELA-007 | accounts | Manter | Financeiro › Contas | Condicional |
| TELA-008 | cash-flow | Unificar | Financeiro › Fluxo (aba) | Condicional |
| TELA-009 | cash-operations | Unificar | Financeiro › Fluxo › Extratos | Condicional |
| TELA-010 | finance-center | Unificar | Financeiro › Conciliação | Condicional |
| TELA-011 | financial-operations-center | Manter | Financeiro › Operações | **Sim (âncora)** |
| TELA-012 | financial-intelligence | Manter | Financeiro › Inteligência | **Sim (âncora)** |
| TELA-013 | financial-monitoring | Eliminar | — (redirect ops-center) | Não |
| TELA-014 | financial-operations | Eliminar | — (redirect ops-center) | Não |
| TELA-015 | sales | Manter | Combustíveis › Vendas | Sim |
| TELA-016 | stock | Corrigir antes | Combustíveis › Tanques | Após fix live |
| TELA-017 | fuels | Corrigir antes | Combustíveis › Bombas | Ocultar se timeout |
| TELA-018 | fuel-executive | Ocultar | Widget Combustíveis/Executivo | Não |
| TELA-019 | lmc-intelligence | Manter | Combustíveis › LMC | Sim |
| TELA-020 | fuel-governance | Manter | Combustíveis › Governança | Sim |
| TELA-021 | non-fuel-products | Manter | Produtos › Vendas (3 abas) | Sim |
| TELA-022 | commercial-copilot | Unificar | Produtos › Oportunidades | Condicional |
| TELA-023 | commercial-execution | Unificar | Produtos › Ações | Sim |
| TELA-024 | commercial-learning | Unificar | Produtos › Resultados | Condicional |
| TELA-025 | nfce-intelligence | Manter | Fiscal › NFCE | Sim |
| TELA-026 | fiscal-reconciliation | Manter | Fiscal › Conciliação | Sim |
| TELA-027 | fiscal-intelligence | Manter | Fiscal › Tributação/Riscos | Sim |
| TELA-028 | administration | Corrigir antes | Admin › Sistema | Não (placeholder) |
| TELA-029 | executive | Ocultar | Widget Executivo | Não |
| TELA-030 | operator-performance | Ocultar | Modo Operação | Não |
| TELA-031 | people-intelligence | Ocultar | Admin › Pessoas | Não |
| TELA-032 | people-roi | Ocultar | Admin › Pessoas | Não |
| TELA-033 | operation-roi | Ocultar | Modo Operação | Não |
| TELA-034 | management-action | Unificar | Executivo › Alertas | Não |
| TELA-035 | benchmark | Ocultar | Widget Scorecard | Não |
| TELA-036 | corporate-hub | Ocultar | Fundir workspace | Não |
| TELA-037 | executive-decision | Ocultar | Modo técnico | Não |
| TELA-038 | executive-copilot | Ocultar | Modo técnico (F05) | Não |
| TELA-039 | recommendations | Ocultar | Modo técnico (F05) | Não |
| TELA-040 | learning | Ocultar | Modo técnico (F05) | Não |

---

## Mapa final enxuto (proposta)

### Regra: 6 macroáreas × até 3 telas principais

#### Menu Executivo (Diretoria)

| # | Tela | View | Abas internas |
|---|---|---|---|
| 1 | Resumo | executive-workspace | — |
| 2 | Indicadores | executive-scorecard | Benchmark (widget) |
| 3 | Alertas | action-center | Metas (004), Gestão (034) |

**Removido do menu:** executive, corporateHub, copilot, recommendations, learning, decision-engine

---

#### Menu Operacional — Financeiro

| # | Tela | View | Abas internas |
|---|---|---|---|
| 1 | Receitas & Despesas | dashboard + expenses | toggle ou sub-abas |
| 2 | Operações Financeiras | financial-operations-center | Saúde snapshot, scheduler |
| 3 | Inteligência Financeira | financial-intelligence | — |

**Unificados como abas (não telas top-level):** Contas (007), Fluxo (008), Extratos (009), Conciliação (010)

**Eliminados:** financial-monitoring, financial-operations (legado)

---

#### Menu Operacional — Combustíveis

| # | Tela | View | Abas internas |
|---|---|---|---|
| 1 | Vendas | sales | — |
| 2 | Estoque & LMC | stock + lmc-intelligence | Tanques | LMC |
| 3 | Governança | fuel-governance | fuel-executive (widget) |

**Oculto até fix:** Bombas (017)

---

#### Menu Operacional — Produtos Vendidos

| # | Tela | View | Abas internas |
|---|---|---|---|
| 1 | Vendas & Mix | non-fuel-products | Vendas, Margem, Mix |
| 2 | Oportunidades | commercial-copilot | — |
| 3 | Ações & Resultados | commercial-execution + learning | Ações | Resultados |

---

#### Menu Operacional — Fiscal

| # | Tela | View | Abas internas |
|---|---|---|---|
| 1 | NFCE | nfce-intelligence | — |
| 2 | Conciliação | fiscal-reconciliation | — |
| 3 | Tributação & Riscos | fiscal-intelligence | Tributação | Riscos |

---

#### Menu Administração (Administrador / TI)

| # | Tela | View | Abas internas |
|---|---|---|---|
| 1 | Sistema | administration | Filiais, Usuários, Permissões, Integrações, Config |
| 2 | Pessoas & ROI | people-intelligence | people-roi (widget) |
| 3 | Diagnóstico técnico | (modo técnico) | circuit-breaker, snapshot-health — **sem tela diretoria** |

**Motores operacionais (modo Operação, não diretoria):** operator-performance, operation-roi

---

## Contagem final proposta

| Camada | Telas |
|---|---|
| Telas principais visíveis | **18** |
| Abas internas (não contam como tela) | **~14** |
| Widgets (embed) | **~6** |
| Ocultas / modo técnico | **10** |
| Eliminadas da navegação | **2** |

---

## Plano de limpeza (ordem recomendada)

### Fase A — Sem código (RT-01 imediato)

1. Documentar escopo RT-01 apenas nas **12 telas indispensáveis**
2. Ignorar 013, 014, 037–040 na bateria de testes
3. Marcar 017, 028 como fora de escopo até correção

### Fase B — Navegação (UX only, pós-RT-01)

1. Remover abas legado monitoring/operations da UX (aliases já redirecionam)
2. Colapsar motor strip F05 — ocultar da diretoria
3. Unificar abas Fluxo/Conciliação financeiro
4. Fundir abas Produtos (execution + learning)

### Fase C — Correções operacionais

1. Receitas (005) — snapshot-first como F08
2. Tanques (016) — resilience pattern
3. Bombas (017) — timeout fuel-summary
4. Administração (028) — CRUD real ou manter só diagnóstico em modo técnico

---

## Matriz domínio × ação

| Macroárea | Manter | Unificar | Ocultar | Eliminar | Corrigir |
|---|---|---|---|---|---|
| Executivo | 3 | 2 | 7 | 0 | 0 |
| Financeiro | 5 | 4 | 1 | 2 | 2 |
| Combustíveis | 3 | 1 | 1 | 0 | 2 |
| Produtos Vendidos | 1 | 3 | 0 | 0 | 0 |
| Fiscal | 3 | 1 | 0 | 0 | 0 |
| Administração | 1 | 0 | 2 | 0 | 1 |
| **Total** | **18** | **12** | **8** | **2** | **8** |

> Unificar e Ocultar podem sobrepor a mesma tela em categorias distintas (ex.: TELA-018 oculta + widget).

---

## Escopo RT-01 pós-corte

### Incluir

```text
F08.3, F08.4, Despesas, Receitas*, Sales,
LMC, Governança, Produtos, NFCE, Conciliação Fiscal, Tributação,
Painel Executivo, Scorecard, Alertas
```

### Excluir

```text
F05 IA (037–040), legado 013–014, Bombas (017) se timeout,
Admin placeholder (028), motores strip ocultos
```

---

```text
[PARECER FINAL: RT-01B INVENTÁRIO EXECUTIVO DE TELAS APROVADO]
```
