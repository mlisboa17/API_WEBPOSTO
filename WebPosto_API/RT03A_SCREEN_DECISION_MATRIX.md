# RT03A — Matriz de Decisão por Tela

**Escopo RT-01:** 18 telas | **Referência RT-01B:** decisões alinhadas

| ID | Tela | View | Macroárea | Valor Executivo | Clareza | Poluição | Hierarquia | Linguagem | Fiori /10 | Decisão RT-03A |
|---|---|---|---|---|---|---|---|---|---|---|
| RT03-001 | Operações Financeiras F08.3 | financial-operations-center | Financeiro | **Baixo** (TI) | Confusa | Poluída | Ruim | Muito técnica | 4 | **OCULTAR** (Admin) |
| RT03-002 | Inteligência Financeira F08.4 | financial-intelligence | Financeiro | **Alto** | Parcial | Moderada | Aceitável | Muito técnica | 7 | **MANTER** |
| RT03-003 | Receitas | dashboard | Financeiro | **Alto** | Clara | Limpa | Boa | Adequada | 7 | **MANTER** |
| RT03-004 | Despesas | expenses | Financeiro | **Alto** | Clara | Moderada | Aceitável | Adequada | 6 | **MANTER** |
| RT03-005 | Produtos — Performance | non-fuel-products | Produtos | **Alto** | Parcial | Poluída | Ruim | Muito técnica | 4 | **UNIFICAR** |
| RT03-006 | Oportunidades | commercial-copilot | Produtos | Médio | Parcial | Moderada | Aceitável | Muito técnica | 5 | **UNIFICAR** |
| RT03-007 | Ações Comerciais | commercial-execution | Produtos | Médio | Parcial | Moderada | Aceitável | Muito técnica | 6 | **UNIFICAR** |
| RT03-008 | Resultados | commercial-learning | Produtos | Médio | Parcial | Moderada | Aceitável | Muito técnica | 6 | **UNIFICAR** |
| RT03-009 | Vendas Combustível | sales | Combustíveis | **Alto** | Clara | Limpa | Boa | Adequada | 7 | **MANTER** |
| RT03-010 | Estoque / Tanques | stock | Combustíveis | Médio | Clara | Limpa | Boa | Adequada | 7 | **MANTER** |
| RT03-011 | Controle LMC | lmc-intelligence | Combustíveis | **Alto** | Parcial | Moderada | Aceitável | Muito técnica | 6 | **MANTER** + renomear |
| RT03-012 | Governança Combustível | fuel-governance | Combustíveis | **Alto** | Parcial | Moderada | Aceitável | Muito técnica | 6 | **MANTER** + renomear |
| RT03-013 | NFCE | nfce-intelligence | Fiscal | **Alto** | Parcial | Moderada | Aceitável | Muito técnica | 6 | **MANTER** + renomear |
| RT03-014 | Conciliação Fiscal | fiscal-reconciliation | Fiscal | **Alto** | Clara | Moderada | Aceitável | Adequada | 7 | **MANTER** |
| RT03-015 | Tributação e Riscos | fiscal-intelligence | Fiscal | **Alto** | Parcial | Moderada | Aceitável | Muito técnica | 6 | **UNIFICAR** (abas NFCE) |
| RT03-016 | Resumo Executivo | executive-workspace | Executivo | **Alto** | Clara | Moderada | Boa | Adequada | 8 | **MANTER** |
| RT03-017 | Indicadores | executive-scorecard | Executivo | Médio | Confusa | Poluída | Ruim | Muito técnica | 5 | **UNIFICAR** → Resumo |
| RT03-018 | Alertas | action-center | Executivo | **Alto** | Parcial | Moderada | Aceitável | Muito técnica | 7 | **MANTER** |

---

## Contagem de decisões (18 telas RT-01)

| Decisão | Qtd | IDs |
|---|---|---|
| **MANTER** | 10 | 002–004, 009–014, 016, 018 |
| **UNIFICAR** | 6 | 005–008, 015, 017 |
| **OCULTAR** | 1 | 001 (F08.3 → Admin/TI) |
| **ELIMINAR** | 0 | — |
| **CORRIGIR ANTES** | 0* | *Renomear EN→PT (011–013) é copy-only, não bloqueia |

---

## Duplicidades confirmadas (UX)

| Par A | Par B | Decisão |
|---|---|---|
| Resumo (016) | Indicadores (017) | Unificar scorecard como aba |
| Produtos Performance (005) | Oportunidades/Ações/Resultados (006–008) | 1 tela, 4 abas |
| NFCE (013) | Tributação (015) | Abas mesma área Fiscal |
| F08.3 (001) | F08.4 (002) | Separar público: TI vs Diretoria |

---

## Telas indispensáveis (decisão em 10s)

```text
RT03-016  Resumo Executivo
RT03-003  Receitas
RT03-004  Despesas
RT03-002  Inteligência Financeira
RT03-018  Alertas
RT03-009  Vendas
RT03-013  NFCE
RT03-014  Conciliação Fiscal
```

---

## Telas claramente técnicas (não diretoria)

```text
RT03-001  F08.3 Operations Center
RT03-017  Executive Scorecard (headers F04.7)
RT03-006  Oportunidades (engine labels)
```

---

## Widgets recomendados (não telas top-level)

| Conteúdo atual | Destino widget |
|---|---|
| Benchmark / conformidade filial | Widget no Resumo ou Governança |
| ROI detalhado comercial | Aba Resultados, não Resumo |
| Timeline scheduler F08.3 | Somente Admin |

---

## Respostas executivas (20)

| # | Resposta |
|---|---|
| 1 | **18** telas avaliadas |
| 2 | UX adequada (BOA/ACEITÁVEL + CLARA): **8** |
| 3 | Confusas: **2** (F08.3, Indicadores) |
| 4 | Poluídas: **3** (F08.3, Produtos Performance, Indicadores) |
| 5 | Permanecer: **10** |
| 6 | Unificar: **6** |
| 7 | Ocultar: **1** (F08.3 diretoria) |
| 8 | Eliminar: **0** |
| 9 | Mais redundância: **Produtos Vendidos** |
| 10 | Mais valor executivo: **Financeiro + Executivo** |
| 11 | Indispensáveis: lista acima (8) |
| 12 | Técnicas: F08.3, Scorecard headers, engines F07 |
| 13 | Legadas: fora escopo RT-01 |
| 14 | Duplicam: Resumo/Indicadores; Produtos 4 telas; NFCE/Riscos |
| 15 | Não apoiam decisão: **F08.3** (infra) |
| 16 | Virar abas: Produtos (4), Fiscal riscos, Metas scorecard |
| 17 | Virar widgets: conformidade, benchmark strip |
| 18 | Entende em <10s? | **Parcial** (3–4 telas sim) |
| 19 | Nota UX executiva | **6,3 / 10** |
| 20 | Limpeza pode começar? | **Sim** — só navegação/copy, sem features |
