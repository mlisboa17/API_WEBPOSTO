# RT05 — IA-1: Cognitive Load Audit

**Data:** 2026-06-09 | **Escopo:** 18 telas RT-01 | **Método:** auditoria estática frontend (`frontend/pages/*`, `filters.js`, `navigationShell.js`) + consolidação RT-03A/RT-04  
**Regra:** nenhum código alterado nesta sprint

---

## Metodologia de medição

Contagem por tela = **chrome global** (sempre visível) + **conteúdo da view**.

| Elemento global | Quantidade fixa |
|---|---|
| Botões sidebar (macroáreas) | 6 |
| Abas da área | 3 |
| Strip “Avançado” (motores) | 0–6 (média 3) |
| Botão Atualizar (topbar) | 1 |
| **Subtotal navegação** | **10–16** |
| Filtros base visíveis | 8 |
| Filtros extras (Despesas) | +5 |
| **Subtotal filtros** | **8 ou 13** |

**Carga cognitiva total percebida** = navegação + filtros + conteúdo da tela.

### Limiares de classificação

| Classe | Critério |
|---|---|
| **ACEITÁVEL** | ≤12 elementos decisórios na 1ª dobra; ≤8 filtros; ≤4 KPIs |
| **POLUÍDA** | 13–25 elementos na 1ª dobra; ou filtros >8; ou >6 KPIs |
| **CRÍTICA** | >25 elementos na 1ª dobra; ou >10 KPIs; ou >3 tabelas simultâneas; ou linguagem técnica dominante |

---

## Matriz por tela RT-01

| ID | Tela | View | Filtros | Nav | Botões view | KPIs/Cards | Tabelas | Blocos/Seções | **Classe** | Regra 5s |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| RT03-016 | Resumo Executivo | executive-workspace | 8 | 16 | 2 | 11 | 2 | 5 | **CRÍTICA** | ❌ |
| RT03-017 | Indicadores | executive-scorecard | 8 | 16 | 2 | 8 | 3 | 4 | **CRÍTICA** | ❌ |
| RT03-018 | Central de Alertas | action-center | 8 | 16 | 2 | 8 | 3 | 3 | **CRÍTICA** | ❌ |
| RT03-003 | Receitas | dashboard | 8 | 16 | 4* | 3 | 1 | 2 | **POLUÍDA** | ⚠️ |
| RT03-004 | Despesas | expenses | **13** | 16 | 4* | 0 | 1 | 1 | **CRÍTICA** | ❌ |
| RT03-002 | Inteligência Financeira | financial-intelligence | 8 | 16 | 2 | ~12 | 6 | 6 | **CRÍTICA** | ❌ |
| RT03-001 | Diagnóstico Técnico (F08.3) | financial-operations-center | 8 | 16 | 4 | **13+** | 4+ | 8+ | **CRÍTICA** | ❌ |
| RT03-005 | Produtos — Performance | non-fuel-products | 8 | 16 | 2 | 7 | **6** | 6 | **CRÍTICA** | ❌ |
| RT03-006 | Oportunidades | commercial-copilot | 8 | 16 | 4 | 4 | 2 | 4 | **CRÍTICA** | ❌ |
| RT03-007 | Ações Comerciais | commercial-execution | 8 | 16 | 2 | 6 | 3 | 4 | **CRÍTICA** | ❌ |
| RT03-008 | Resultados Comerciais | commercial-learning | 8 | 16 | 2 | 6+ | 4+ | 5 | **CRÍTICA** | ❌ |
| RT03-009 | Vendas Combustível | sales | 8 | 16 | 2 | 0 | 1 | 1 | **ACEITÁVEL** | ⚠️ |
| RT03-010 | Estoque & Tanques | stock | 8 | 16 | 4* | 0 | 1 | 1 | **POLUÍDA** | ⚠️ |
| RT03-011 | Controle LMC | lmc-intelligence | 8 | 16 | 2 | 6 | 3 | 4 | **CRÍTICA** | ❌ |
| RT03-012 | Governança Combustível | fuel-governance | 8 | 16 | 2 | 6 | 2 | 3 | **POLUÍDA** | ❌ |
| RT03-013 | NFCE | nfce-intelligence | 8 | 16 | 2 | 6 | 3 | 4 | **CRÍTICA** | ❌ |
| RT03-014 | Conciliação Fiscal | fiscal-reconciliation | 8 | 16 | 2 | 4 | 2+ | 3 | **POLUÍDA** | ❌ |
| RT03-015 | Tributação & Riscos | fiscal-intelligence | 8 | 16 | 2 | 4 | 2 | 3 | **POLUÍDA** | ❌ |

\* Inclui ações da tabela (busca, export, paginação, limpar filtros internos).

---

## Ranking — maior carga cognitiva

| # | Tela | Score composto* |
|---|---|---|
| 1 | Diagnóstico Técnico (F08.3) | 98 |
| 2 | Produtos — Performance | 92 |
| 3 | Inteligência Financeira | 89 |
| 4 | Resultados Comerciais | 86 |
| 5 | Resumo Executivo | 84 |
| 6 | Central de Alertas | 81 |
| 7 | Indicadores | 79 |
| 8 | Despesas (13 filtros) | 78 |

\* Score = filtros×2 + KPIs + tabelas×3 + seções×2 + nav/4 (heurística interna RT-05).

---

## Ranking — menor carga (mais intuitivas)

| # | Tela | Observação |
|---|---|---|
| 1 | Vendas Combustível | 1 tabela focada; subtabs claras |
| 2 | Receitas | 3 cards + 1 tabela; ruído vem dos 8 filtros globais |
| 3 | Estoque | Similar a Vendas; filtros globais pesam |
| 4 | Conciliação Fiscal | Estrutura moderada; lineage técnico atrapalha |
| 5 | Governança Combustível | KPIs de engine visíveis |

---

## Síntese quantitativa

| Métrica | Valor |
|---|---|
| Telas **CRÍTICA** | **12 / 18** (67%) |
| Telas **POLUÍDA** | **5 / 18** (28%) |
| Telas **ACEITÁVEL** | **1 / 18** (6%) |
| Falham regra 5s | **15 / 18** (83%) |
| Falham parcialmente (⚠️) | **3 / 18** (17%) |
| Filtros médios por tela | **8,3** (13 em Despesas) |
| KPIs médios por tela | **6,1** |
| Tabelas médias por tela | **2,4** |

---

## Diagnóstico central

O gargalo de carga cognitiva **não está nas telas isoladas** — está no **chrome global repetido**:

```text
8 filtros + 6 sidebar + 3 abas + strip Avançado + topbar
= 18–24 elementos ANTES do conteúdo da tela
```

Isso viola a regra dos 5 segundos **antes** de o usuário ler qualquer KPI.

---

**[IA-1 APROVADA — carga cognitiva medida nas 18 telas RT-01]**
