# RT01B — Inventário Executivo de Telas

**Data:** 2026-06-09 | **Base:** RT-00 + `frontend/config/navigation.js` + `frontend/app.js`  
**Escopo:** decisão de produto — **nenhuma funcionalidade nova criada**

---

## Síntese para diretoria

| Métrica | Hoje | Recomendação pós-limpeza |
|---|---|---|
| Telas mapeadas (`?view=`) | **40** | **18 telas principais** |
| Dashboards comprovados (<3s) | 2 | 2 (mantidos como âncora) |
| Telas a manter como principal | — | **18** |
| Telas a unificar (aba/widget) | — | **12** |
| Telas a ocultar | — | **8** |
| Telas a eliminar da navegação | — | **2** (+ aliases legados) |
| Corrigir antes da RT-01 | — | **8** |

> **Princípio:** reduzir de 40 entradas cognitivas para **6 macroáreas × até 3 telas principais**, com abas internas onde necessário.

---

## Critérios aplicados

1. Não apoia decisão → Ocultar ou Eliminar  
2. Motor interno / engine → Widget ou modo técnico  
3. Duplica outra tela → Unificar  
4. Legado substituído → Eliminar da navegação  
5. Não operacional → Corrigir antes ou excluir RT-01  
6. Valor baixo para diretoria → Ocultar (Administração / modo técnico)

---

## Matriz Executiva — 40 telas

| ID | Tela / View | Nome Funcional | Macroárea | Valor para o Negócio | Usuário-Alvo | Decisão que Apoia | Status de Análise | Impacto | Ação Recomendada | Observação |
|---|---|---|---|---|---|---|---|---|---|---|
| TELA-001 | `?view=executive-workspace` | Painel Executivo | Executivo | Visão consolidada rede/filial; priorização do dia | Diretoria | priorizar filial; agir sobre risco | **Manter** | Alto | Manter como tela principal (aba Resumo) | Snapshot parcial; RT-01 elegível |
| TELA-002 | `?view=executive-scorecard` | Indicadores Executivos | Executivo | KPIs de performance da rede | Diretoria | acompanhar margem; comparar filiais | **Manter** | Alto | Manter como aba Indicadores | Cockpit snapshot OK |
| TELA-003 | `?view=action-center` | Central de Alertas | Executivo | Concentra exceções e pendências | Diretoria / Operação | agir sobre risco financeiro | **Manter** | Alto | Manter como aba Alertas | Snapshot read |
| TELA-004 | `?view=goals-campaigns` | Metas e Campanhas | Executivo | Acompanha metas comerciais/operacionais | Diretoria / Comercial | priorizar ação comercial | **Unificar** | Médio | Transformar em aba dentro de Executivo | Pode fundir com scorecard |
| TELA-005 | `?view=dashboard` | Receitas e Resultado | Financeiro | Receita, caixa e visão financeira agregada | Financeiro / Diretoria | acompanhar margem; fluxo de caixa | **Corrigir antes** | Alto | Manter; corrigir live lento antes RT-01 | Live >22s; duplicada em Executivo (motor) |
| TELA-006 | `?view=expenses` | Despesas | Financeiro | Controle e auditoria de gastos | Financeiro | reduzir despesa | **Manter** | Alto | Manter como aba principal | Resilience F08 OK; RT-01 elegível |
| TELA-007 | `?view=accounts` | Contas a Pagar | Financeiro | Obrigações e vencimentos | Financeiro | reduzir despesa; priorizar pagamento | **Manter** | Médio | Manter como aba Contas | PARCIAL live |
| TELA-008 | `?view=cash-flow` | Fluxo de Caixa | Financeiro | Entradas/saídas e liquidez | Financeiro | acompanhar margem | **Unificar** | Médio | Transformar em aba do Financeiro | Snapshot pequeno; fundir com Receitas |
| TELA-009 | `?view=cash-operations` | Extratos e Movimentação | Financeiro | Conciliação operacional de caixa | Financeiro | validar caixa | **Unificar** | Médio | Aba interna de Fluxo/Conciliação | Overlap com financeCenter |
| TELA-010 | `?view=finance-center` | Conciliação Financeira | Financeiro | Fechamento e conciliação | Financeiro | agir sobre risco financeiro | **Unificar** | Médio | Aba Conciliação (1 experiência) | Unificar 008–010 |
| TELA-011 | `?view=financial-operations-center` | Operações Financeiras | Financeiro | Cockpit operacional F08.3 (snapshots, saúde, scheduler) | Financeiro / Diretoria | monitorar snapshot; agir sobre risco | **Manter** | Alto | Manter como tela principal | **OPERACIONAL** <3s; RT-01 âncora |
| TELA-012 | `?view=financial-intelligence` | Inteligência Financeira | Financeiro | Score, tendências e riscos F08.4 | Diretoria / Financeiro | agir sobre risco financeiro | **Manter** | Alto | Manter como tela principal | **OPERACIONAL** <3s; RT-01 âncora |
| TELA-013 | `?view=financial-monitoring` | Monitoramento Financeiro (legado) | Financeiro | Duplicava F08.2 | — | — | **Eliminar** | Baixo | Eliminar da navegação | Alias → operations-center; página legado órfã |
| TELA-014 | `?view=financial-operations` | Operações Financeiras (legado) | Financeiro | Duplicava F08.2 | — | — | **Eliminar** | Baixo | Eliminar da navegação | Alias → operations-center; redundante com TELA-011 |
| TELA-015 | `?view=sales` | Vendas de Combustível | Combustíveis | Volume e receita de combustíveis | Operação / Comercial | acompanhar margem | **Manter** | Alto | Manter; hotfix P0 validado | ~8s snapshot fallback; RT-01 elegível |
| TELA-016 | `?view=stock` | Tanques e Estoque | Combustíveis | Nível de estoque e ruptura | Operação | corrigir LMC; evitar ruptura | **Corrigir antes** | Médio | Manter após estabilizar live | Live >22s |
| TELA-017 | `?view=fuels` | Bombas e Abastecimentos | Combustíveis | Performance por bomba | Operação | priorizar filial | **Corrigir antes** | Médio | Ocultar até RT-01 se timeout persistir | fuel-summary ~54s |
| TELA-018 | `?view=fuel-executive` | Combustível Executivo | Combustíveis | Visão executiva combustível | Diretoria | acompanhar margem | **Ocultar** | Médio | Widget no Executivo ou Combustíveis | Motor strip; API OK ~4s |
| TELA-019 | `?view=lmc-intelligence` | Controle LMC | Combustíveis | Perdas, medição e conformidade LMC | Operação / Fiscal | corrigir LMC | **Manter** | Alto | Manter como aba LMC | Cockpit snapshot OK |
| TELA-020 | `?view=fuel-governance` | Governança de Combustíveis | Combustíveis | Regras, desvios e governança | Operação / Diretoria | reduzir perda | **Manter** | Alto | Manter como aba Governança | RT-01 elegível |
| TELA-021 | `?view=non-fuel-products` | Produtos Vendidos | Produtos Vendidos | Vendas, mix e margem não-combustível | Comercial / Diretoria | acompanhar margem; mix | **Manter** | Alto | 1 tela com abas Vendas/Margem/Mix | 3 abas UX apontam mesma view |
| TELA-022 | `?view=commercial-copilot` | Oportunidades Comerciais | Produtos Vendidos | Sugestões de ação comercial | Comercial | priorizar SKU/filial | **Unificar** | Médio | Aba Oportunidades (já na UX) | Experimental F07 |
| TELA-023 | `?view=commercial-execution` | Plano de Ações Comerciais | Produtos Vendidos | Execução de ações | Comercial / Operação | priorizar ação comercial | **Unificar** | Médio | Unificar com Resultados (1 fluxo) | Cockpit OK |
| TELA-024 | `?view=commercial-learning` | Resultados Comerciais | Produtos Vendidos | Aprendizado pós-ação | Comercial | ajustar mix | **Unificar** | Baixo | Aba Resultados; fundir com 023 | Overlap execution/learning |
| TELA-025 | `?view=nfce-intelligence` | NFCE e Emissões | Fiscal | Conformidade e volume NFC-e | Fiscal | validar NFCE | **Manter** | Alto | Manter como aba NFCE | RT-01 elegível |
| TELA-026 | `?view=fiscal-reconciliation` | Conciliação Fiscal | Fiscal | Cruzamento fiscal vs operacional | Fiscal / Financeiro | validar NFCE; reduzir risco | **Manter** | Alto | Manter como aba Conciliação | RT-01 elegível |
| TELA-027 | `?view=fiscal-intelligence` | Tributação e Riscos Fiscais | Fiscal | Exposição tributária e riscos | Fiscal / Diretoria | reduzir risco fiscal | **Manter** | Alto | 1 aba (Tributação + Riscos) | 2 abas UX → mesma view |
| TELA-028 | `?view=administration` | Administração do Sistema | Administração | Filiais, usuários, integrações | Administrador | configurar integrações | **Corrigir antes** | Médio | Manter estrutura; implementar CRUD depois | UI placeholder hoje |
| TELA-029 | `?view=executive` | Painel Executivo (live) | Executivo | Visão live alternativa | Diretoria | acompanhar margem | **Ocultar** | Baixo | Unificar com TELA-001 ou widget | Duplica workspace; live lento |
| TELA-030 | `?view=operator-performance` | Desempenho de Operadores | Financeiro | Performance por operador | Operação | priorizar treinamento | **Ocultar** | Baixo | Modo Operação (não diretoria) | Motor strip F04 |
| TELA-031 | `?view=people-intelligence` | Inteligência de Pessoas | Executivo | Análise de equipe | Operação / Admin | alocar equipe | **Ocultar** | Baixo | Administração ou modo técnico | Motor strip |
| TELA-032 | `?view=people-roi` | ROI de Pessoas | Executivo | Retorno por colaborador | Operação | alocar equipe | **Ocultar** | Baixo | Widget em People (Admin) | Motor strip |
| TELA-033 | `?view=operation-roi` | ROI Operacional | Executivo | Retorno por operação | Operação | priorizar filial | **Ocultar** | Baixo | Widget Operação | Motor strip |
| TELA-034 | `?view=management-action` | Ações de Gestão | Executivo | Plano gerencial | Diretoria | agir sobre risco | **Ocultar** | Médio | Unificar com action-center | Overlap TELA-003 |
| TELA-035 | `?view=benchmark` | Benchmark de Rede | Executivo | Comparação entre filiais | Diretoria | priorizar filial | **Ocultar** | Médio | Widget no Scorecard | Motor técnico F04 |
| TELA-036 | `?view=corporate-hub` | Hub Corporativo | Executivo | Visão corporativa agregada | Diretoria | decisão estratégica | **Ocultar** | Baixo | Fundir em workspace | Experimental |
| TELA-037 | `?view=executive-decision` | Motor de Decisão | Executivo | Engine de decisão F05 | — | — | **Ocultar** | Baixo | Modo técnico / eliminar da diretoria | Nome técnico; F05 experimental |
| TELA-038 | `?view=executive-copilot` | Copiloto Executivo (IA) | Executivo | Assistente IA generativo | Diretoria | apoio à decisão | **Ocultar** | Baixo | Fora RT-01; F05 experimental | IA generativa |
| TELA-039 | `?view=recommendations` | Recomendações Automáticas | Executivo | Engine de recomendação F05 | — | — | **Ocultar** | Baixo | Modo técnico | Não apoia decisão comprovada |
| TELA-040 | `?view=learning` | Aprendizado Contínuo (IA) | Executivo | Closed-loop learning F05 | — | — | **Ocultar** | Baixo | Modo técnico | Engine, não tela de usuário |

---

## Telas indispensáveis (RT-01 + diretoria)

```text
TELA-011  Operações Financeiras (F08.3)
TELA-012  Inteligência Financeira (F08.4)
TELA-006  Despesas
TELA-005  Receitas (após correção live)
TELA-015  Vendas Combustível
TELA-019  LMC
TELA-020  Governança Combustível
TELA-021  Produtos Vendidos
TELA-025  NFCE
TELA-026  Conciliação Fiscal
TELA-027  Tributação/Riscos
TELA-001  Painel Executivo
```

---

## Telas claramente técnicas (ocultar da diretoria)

```text
TELA-037 executive-decision
TELA-038 executive-copilot
TELA-039 recommendations
TELA-040 learning
TELA-013/014 legado monitoring/operations (eliminar)
Motores F04: benchmark, corporateHub, people*, operationRoi, operatorPerformance
```

---

## Duplicidades identificadas

| Grupo | Telas | Decisão |
|---|---|---|
| F08 legado vs novo | 013, 014 → 011, 012 | **Eliminar** 013/014 |
| Receitas | 005 dashboard + 029 executive | **Unificar** |
| Fluxo/conciliação | 008, 009, 010 | **Unificar** 1 experiência |
| Comercial F07 | 022, 023, 024 | **Unificar** 2 abas (Oportunidades + Ações/Resultados) |
| Fiscal riscos | 027 (2 abas UX) | **Unificar** abas |
| Alertas/gestão | 003, 034 | **Unificar** |
| Produtos abas | 021 (3 abas → 1 view) | **Manter** 1 tela, abas internas |

---

## Respostas executivas (20 perguntas)

| # | Resposta |
|---|---|
| 1 | **40** telas avaliadas |
| 2 | **18** devem ser mantidas como telas principais |
| 3 | **12** devem ser unificadas (abas/widgets) |
| 4 | **2** eliminadas da navegação (013, 014 legado) |
| 5 | **8** ocultadas da diretoria (motores F04/F05 + fuel-executive) |
| 6 | **8** precisam correção antes RT-01 (005, 016, 017, 028 + live parcial) |
| 7 | Maior redundância: **Financeiro** (14 views, 4 legados/duplicados) |
| 8 | Maior valor diretoria: **Financeiro** (F08.3 + F08.4) |
| 9 | Indispensáveis: lista acima (12 telas) |
| 10 | Técnicas: 037–040 + motores strip F04/F05 |
| 11 | Legadas: 013, 014 (+ páginas JS órfãs monitoring/operations) |
| 12 | Duplicam: grupos na tabela acima |
| 13 | Não apoiam decisão: 037–040, 013–014, corporateHub experimental |
| 14 | Virar abas: 008–010, 022–024, 027, 004 |
| 15 | Virar widgets: 018, 035, 032–033, 030 |
| 16 | Fora RT-01: 037–040, 013–014, 029, gateway, admin placeholder |
| 17 | Menu executivo final: ver `RT01B_SCREEN_CUT_MATRIX.md` |
| 18 | Menu operacional final: ver matriz |
| 19 | Menu técnico/admin final: ver matriz |
| 20 | **Sim** — limpeza pode começar (somente navegação/UX, sem features) |

---

```text
[PARECER FINAL: RT-01B INVENTÁRIO EXECUTIVO DE TELAS APROVADO]
```
