# RT-07 — IA-1: Screen Consolidation

**Data:** 2026-06-09  
**Regra:** Toda ação remove complexidade?  
**Meta:** ~40 telas → 18 úteis → 12–15 principais · sem perda funcional

---

## 1. Inventário atual

| Camada | Quantidade | Detalhe |
|--------|------------|---------|
| Seções DOM (`index.html`) | **39 views** | Cada `<section id="*View">` |
| Arquivos `frontend/pages/` | **41** | Inclui wrappers (`financialOverview`, `financialExpenses`) |
| Abas principais (nav) | **18** | 3 × 6 macroáreas |
| Motores / Avançado (nav) | **12** | Faixa `motor-strip` |
| **Total navegável** | **30** | Abas + motores |
| Deep links órfãos | **9** | Fora da nav, ainda no DOM |

---

## 2. Mapa completo — classificação

### Executivo (6 navegáveis)

| View | Label nav | Classificação | Destino RT-07 |
|------|-----------|---------------|---------------|
| `executiveWorkspace` | Resumo | **MANTER** | Tela principal |
| `executiveScorecard` | Indicadores | **MANTER** | Aba 3 |
| `actionCenter` | Alertas | **MANTER** | Aba 2 |
| `goalsCampaign` | Metas | **OCULTAR** | Widget no Resumo → detalhe |
| `benchmark` | Comparativo de rede | **UNIFICAR** | Seção dentro de Indicadores |
| `corporateHub` | Visão corporativa | **UNIFICAR** | Seção dentro de Resumo |
| `executive` | *(legado, fora nav)* | **ELIMINAR** | Remover DOM + roteamento |

### Financeiro (7 navegáveis)

| View | Label | Classificação | Destino RT-07 |
|------|-------|---------------|---------------|
| `dashboard` | Receitas | **UNIFICAR** | Aba “Visão” do hub Financeiro |
| `expenses` | Despesas | **UNIFICAR** | Aba “Despesas” do hub Financeiro |
| `financialIntelligence` | Intel. Financeira | **MANTER** | Aba 3 |
| `accounts` | Contas a pagar | **UNIFICAR** | Sub-aba Tesouraria |
| `cashFlow` | Fluxo de caixa | **UNIFICAR** | Sub-aba Tesouraria |
| `cashOperations` | Extratos | **UNIFICAR** | Sub-aba Tesouraria |
| `financeCenter` | Conciliação | **UNIFICAR** | Sub-aba Tesouraria |

### Combustíveis (6 navegáveis)

| View | Label | Classificação | Destino RT-07 |
|------|-------|---------------|---------------|
| `sales` | Vendas | **MANTER** | Aba 1 |
| `stock` | Estoque & Tanques | **MANTER** | Aba 2 |
| `fuelGovernance` | Governança | **MANTER** | Aba 3 |
| `lmcIntelligence` | Controle LMC | **OCULTAR** | Detalhe em Estoque |
| `fuels` | Bombas | **OCULTAR** | Detalhe em Vendas |
| `fuelExecutive` | Visão exec. | **ELIMINAR** | Duplicata de Vendas; motor quebrado no roteamento |

### Produtos Vendidos (4 navegáveis)

| View | Label | Classificação | Destino RT-07 |
|------|-------|---------------|---------------|
| `nonFuelProducts` | Vendas & Mix | **MANTER** | Tela única principal |
| `commercialCopilot` | Oportunidades | **UNIFICAR** | Aba interna “Oportunidades” |
| `commercialLearning` | Resultados | **UNIFICAR** | Aba interna “Resultados” |
| `commercialExecution` | Plano de ações | **OCULTAR** | Widget no detalhe |

### Fiscal (3 navegáveis)

| View | Label | Classificação | Destino RT-07 |
|------|-------|---------------|---------------|
| `nfceIntelligence` | NFCE | **MANTER** | Aba 1 |
| `fiscalReconciliation` | Conciliação | **MANTER** | Aba 2 |
| `fiscalIntelligence` | Tributação & Riscos | **MANTER** | Aba 3 |

### Administração (4 navegáveis)

| View | Label | Classificação | Destino RT-07 |
|------|-------|---------------|---------------|
| `administration` | Sistema | **MANTER** | Aba 1 |
| `financialOperationsCenter` | Diagnóstico Técnico | **MANTER** | Aba 2 |
| `operatorPerformance` | Desempenho operadores | **OCULTAR** | Sub-seção Admin (RH operacional) |
| `peopleIntelligence` | Gestão de pessoas | **OCULTAR** | Sub-seção Admin |

### Órfãs — ELIMINAR (9)

| View | Motivo |
|------|--------|
| `executiveCopilot` | Motor executivo duplicado; valor no Resumo |
| `recommendations` | “Autonomous Recommendation Engine” — técnico |
| `learning` | “Closed Loop Learning Engine” — técnico |
| `executiveDecision` | Decision engine — sem nav |
| `managementAction` | Duplica Alertas |
| `peopleRoi` | ROI técnico — Admin |
| `operationRoi` | ROI técnico — Admin |
| `financialMonitoring` | Redireciona p/ Diagnóstico — remover view |
| `financialOperations` | Redireciona p/ Diagnóstico — remover view |

---

## 3. Contagem projetada

| Estado | Telas principais (nav) | Telas úteis (com sub-abas UX) | Views DOM |
|--------|------------------------|-------------------------------|-----------|
| **Atual** | 18 abas + 12 motores = 30 | 39 | 39 |
| **Meta RT-07** | **15 abas** | **18 experiências** | **~22** |
| **Redução** | −50% motores | −54% DOM | −44% |

### 15 telas principais propostas

1. Resumo · 2. Alertas · 3. Indicadores  
4. Financeiro (hub) · 5. Intel. Financeira · 6. Tesouraria  
7. Vendas Combustível · 8. Estoque · 9. Governança  
10. Produtos Vendidos (hub)  
11. NFCE · 12. Conciliação · 13. Tributação  
14. Sistema · 15. Diagnóstico Técnico  

*(Produtos = 1 entrada com 3 sub-abas internas; Financeiro = 2 entradas + hub com 2 sub-abas)*

---

## 4. Plano de execução (UX only)

| Fase | Ação | Remove complexidade? |
|------|------|----------------------|
| P0 | Eliminar 9 views órfãs do DOM e `app.js` | ✓ |
| P0 | Remover `executive` legado | ✓ |
| P1 | Hub Financeiro: subtabs Receitas/Despesas (mesmas APIs) | ✓ |
| P1 | Hub Tesouraria: subtabs Fluxo/Contas/Extratos/Conciliação | ✓ |
| P1 | Hub Produtos: subtabs Mix/Oportunidades/Resultados | ✓ |
| P2 | Motores → widgets no `<details>` das telas pai | ✓ |
| P2 | Remover faixa `motor-strip` onde hub absorver | ✓ |

**Sem alterar:** endpoints, serviços, motores backend, regras de negócio.

---

## 5. Riscos

| Risco | Mitigação |
|-------|-----------|
| Deep links quebrados | Redirect 301 em `VIEW_ALIASES` |
| Bookmarks antigos | Aliases permanentes por 1 release |
| Perda funcional | Sub-abas renderizam mesmos `render*` atuais |

---

**IA-1 — Conclusão:** Consolidação **viável** de 39 → **~18 experiências** e **15 entradas de menu**, **zero perda funcional** via hubs e sub-abas UX.
