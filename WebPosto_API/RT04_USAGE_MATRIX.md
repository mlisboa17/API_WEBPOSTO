# RT04 — IA-5: Matriz de Utilização

**Data:** 2026-06-09 | **Escopo:** 18 telas RT-01 | **Evidência:** `scripts/rt04_usage_data.json`

**Legenda uso:** ALTA = diário provável · MÉDIA = semanal · BAIXA = esporádico · NULA = não aberta na jornada / motor oculto

---

## Matriz completa

| ID | Tela | View | Perfil principal | Uso | Diário? | Valor |
|---|---|---|---|---|---|---|
| EXEC-RES | Resumo Executivo | executiveWorkspace | Diretoria | **ALTA** | Sim | ALTO |
| EXEC-ALR | Central de Alertas | actionCenter | Diretoria, Operação | **ALTA** | Sim | ALTO |
| FIN-REC | Receitas e Resultado | dashboard | Diretoria, Financeiro | **ALTA** | Sim | ALTO |
| FIN-DESP | Despesas | expenses | Financeiro | **ALTA** | Sim | ALTO |
| COMB-VEND | Vendas Combustível | sales | Operação | **ALTA** | Sim | ALTO |
| FISC-NFCE | Inteligência NFCE | nfceIntelligence | Fiscal | **ALTA** | Sim | ALTO |
| FIN-INT | Inteligência Financeira | financialIntelligence | Diretoria, Financeiro | **MÉDIA** | Não | ALTO |
| EXEC-IND | Indicadores | executiveScorecard | Diretoria | **MÉDIA** | Não | MÉDIO |
| COMB-EST | Estoque & Tanques | stock | Operação | **MÉDIA** | Sim | MÉDIO |
| COMB-GOV | Governança Combustível | fuelGovernance | Operação | **MÉDIA** | Não | MÉDIO |
| PROD-MIX | Vendas & Mix | nonFuelProducts | Comercial | **MÉDIA** | Não | MÉDIO |
| FISC-CONC | Conciliação Fiscal | fiscalReconciliation | Fiscal | **MÉDIA** | Não | ALTO |
| FISC-TRIB | Tributação & Riscos | fiscalIntelligence | Fiscal | **MÉDIA** | Não | MÉDIO |
| ADM-SIS | Sistema | administration | Administrador | **MÉDIA** | Não | MÉDIO |
| PROD-OPP | Oportunidades | commercialCopilot | Comercial | **BAIXA** | Não | BAIXO |
| PROD-RES | Resultados Comerciais | commercialLearning | Comercial | **BAIXA** | Não | BAIXO |
| ADM-DIAG | Diagnóstico Técnico | financialOperationsCenter | Administrador | **BAIXA** | Não | BAIXO* |
| COMB-LMC | Controle LMC (motor) | lmcIntelligence | Operação | **NULA**† | Não | MÉDIO |

\* Valor alto para TI; baixo para negócio.  
† Não aberta espontaneamente; substituída por Governança/Estoque na rotina observada.

---

## Contagem

| Nível | Qtd | % |
|---|---|---|
| **ALTA** | **6** | 33% |
| **MÉDIA** | **8** | 44% |
| **BAIXA** | **3** | 17% |
| **NULA** | **1** | 6% |

> Nota: 6 telas ALTA + 8 MÉDIA = 14 com uso regular; 3 BAIXA + 1 NULA = 4 com uso marginal.

---

## Motores nunca abertos (15 views)

```text
goalsCampaign · benchmark · corporateHub
accounts · cashFlow · cashOperations · financeCenter
fuels · fuelExecutive · commercialExecution
operatorPerformance · peopleIntelligence
executiveCopilot · recommendations · learning
```

**Classificação global motores:** uso **NULA** na jornada observada (acessíveis via deep link, não descobertos).

---

## Heatmap por macroárea

| Macroárea | ALTA | MÉDIA | BAIXA | NULA |
|---|---|---|---|---|
| Executivo | 2 | 1 | 0 | 0 |
| Financeiro | 2 | 1 | 0 | 0 |
| Combustíveis | 1 | 2 | 0 | 1 |
| Produtos | 0 | 1 | 2 | 0 |
| Fiscal | 1 | 2 | 0 | 0 |
| Administração | 0 | 1 | 1 | 0 |

---

**[IA-5 APROVADA — matriz de utilização preenchida]**
