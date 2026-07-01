# RT05 MASTER — Screen Simplification Matrix

**Data:** 2026-06-09 | **Escopo:** 18 telas RT-01 | **Somente plano UX — sem implementação**

Legenda: **M** Manter · **R** Reduzir · **O** Reorganizar · **H** Ocultar

---

## Matriz completa

| ID | Tela | M | R | O | H | Antes (elem.*) | Depois (elem.*) | Removidos |
|---|---|---|---|---|---:|---:|---:|
| RT03-016 | Resumo Executivo | KPIs rede | alertas 8→3 | 5 blocos→3 dobras | execução ROI | 28 | 14 | **14** |
| RT03-017 | Indicadores | score 4 | KPIs 8→4 | unificar→Resumo | JSON, paridade | 24 | 10 | **14** |
| RT03-018 | Alertas | tabelas P1 | KPIs 8→4 | alertas 1ª dobra | ROI Δ, auditável | 22 | 11 | **11** |
| RT03-003 | Receitas | cards 3 | filtros 8→**2** | gráfico 1ª dobra | filtros coluna | 18 | 10 | **8** |
| RT03-004 | Despesas | tabela | filtros 13→**2** | KPIs resumo | 11 filtros avanç. | 20 | 9 | **11** |
| RT03-002 | Intel. Financeira | score+riscos | seções 6→3 | 4 KPIs top | fluxo/commitments default | 26 | 12 | **14** |
| RT03-001 | F08.3 Diagnóstico | — | — | — | **tudo p/ Admin TI** | 35+ | 35+† | 0‡ |
| RT03-005 | Produtos Performance | pareto | KPIs 7→4 | 1 tabela 1ª dobra | 5 tabelas, R04 | 32 | 12 | **20** |
| RT03-006 | Oportunidades | sugestões | copilot ask | 2ª dobra | lineage | 18 | 8 | **10** |
| RT03-007 | Ações Comerciais | plano | KPIs | unificar Produtos | motor strip | 20 | 10 | **10** |
| RT03-008 | Resultados | ROI negócio | KPIs 6→3 | aba Produtos | calibration | 24 | 9 | **15** |
| RT03-009 | Vendas | tabela | filtros 8→3 | subtabs | filtros coluna | 14 | 8 | **6** |
| RT03-010 | Estoque | tabela | filtros 8→3 | KPIs nível | — | 14 | 8 | **6** |
| RT03-011 | LMC | conformidade | KPIs 6→4 | 2ª dobra | engine labels | 22 | 10 | **12** |
| RT03-012 | Governança | alertas LMC | KPIs 6→4 | 2ª dobra | delay engine | 18 | 10 | **8** |
| RT03-013 | NFCE | volume/conc. | KPIs 6→4 | 2ª dobra | anomaly engine | 22 | 10 | **12** |
| RT03-014 | Conciliação Fiscal | divergências | KPIs 4→4 | 2ª dobra | lineage table | 16 | 9 | **7** |
| RT03-015 | Tributação | riscos top | KPIs 4→4 | unificar NFCE | tax engine | 16 | 9 | **7** |

\* Elementos visíveis estimados (KPIs + tabelas + seções + filtros + botões view).  
† F08.3 permanece intacto para Admin — oculto da jornada diretoria.  
‡ Remoção = ocultação da experiência executiva, não delete de código.

---

## Totais consolidados

| Métrica | Valor |
|---|---|
| Elementos visuais **antes** (soma) | **~392** |
| Elementos visuais **depois** (soma) | **~186** |
| **Elementos removidos/ocultos** | **~206** (**52,6%**) |
| Cards redundantes elimináveis | **~38** |
| KPIs redundantes elimináveis | **~42** |
| Tabelas candidatas a drill-down | **22 / ~35** |

---

## Ações por decisão

### Manter (conteúdo core)

Resumo, Receitas, Despesas, Alertas, Vendas, NFCE, Conciliação — **estrutura de dados preservada**.

### Reduzir (densidade)

KPIs, filtros, alertas simultâneos, tabelas paralelas.

### Reorganizar (dobras)

1ª dobra decisória · 2ª operacional · 3ª técnica.

### Ocultar (perfil diretoria)

F08.3, motores strip, lineage, engines, calibration, JSON debug, KPIs ROI técnico.

---

## Telas prioritárias de simplificação

| Prioridade | Tela | Motivo |
|---|---|---|
| P0 | Produtos Performance | 6 tabelas + 7 KPIs |
| P0 | Despesas | 13 filtros na 1ª dobra |
| P0 | Resumo Executivo | 5 blocos competindo |
| P1 | Inteligência Financeira | 6 seções |
| P1 | Indicadores | Redundante + JSON |
| P1 | Resultados Comerciais | Engines visíveis |

---

**[IA-5 APROVADA — matriz de simplificação com ~207 elementos removíveis]**
