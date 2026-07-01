# RT-07 — IA-5: Technical Language Elimination

**Objetivo:** Zero linguagem técnica na camada executiva.  
**Destino:** Administração · Diagnóstico Técnico

---

## 1. Termos proibidos na UI executiva

| Termo técnico | Ocorrências UI | Camada atual | Ação RT-07 |
|---------------|----------------|--------------|------------|
| **snapshot** | `executiveDashboard`, banner resiliência, status bars | Receitas/Despesas/legado | **Remover** ou renomear “Última atualização” |
| **lineage** | `executiveDashboard`, `fiscalReconciliation` (detalhe) | Legado / detalhe fiscal | Manter só Admin; renomear detalhe → “Origem dos dados” |
| **gateway** | Admin integrações | Admin | OK |
| **health / saúde** | Banner, fin-ops, scorecards | Receitas + Admin | **Remover** da 1ª dobra executiva |
| **scheduler** | `financialOperations*` | Diagnóstico | OK (Admin) |
| **circuit breaker** | Banner, Admin | Receitas + Admin | **Remover** executivo |
| **engine** | Títulos de tela | Várias órfãs | **Eliminar telas** |
| **learning** | `learning.js`, colunas CSV | Órfã | **Eliminar tela** |
| **copilot** | `commercialCopilot`, `executiveCopilot` | Produtos + órfã | **Renomear** UI |

---

## 2. Títulos a corrigir (executivo → negócio)

| Arquivo | Título atual | Título RT-07 |
|---------|--------------|--------------|
| `learning.js` | Closed Loop Learning Engine | *(eliminar view)* |
| `recommendations.js` | Autonomous Recommendation Engine | *(eliminar view)* |
| `executiveCopilot.js` | Executive Copilot | *(eliminar ou merge Resumo)* |
| `executiveDecision.js` | Decision Engine | *(eliminar)* |
| `managementAction.js` | Management Action Center | Alertas (merge) |
| `corporateHub.js` | Corporate Intelligence Hub | Visão da rede |
| `benchmark.js` | Benchmark Intelligence | Comparativo de rede |
| `goalsCampaign.js` | Goals & Campaigns | Metas e campanhas |
| `financeCenter.js` | Centro Financeiro Corporativo | Conciliação financeira |
| `cashOperations.js` | Cash Operations | Extratos de caixa |
| `financialOperations.js` | Operações Financeiras Autônomas | *(eliminar view)* |
| `nfceIntelligence.js` | Inteligência NFCE | NFCE — riscos e divergências |

---

## 3. Banner resiliência (`financialResilienceBanner.js`)

**Texto atual expõe:** origem, idade snapshot, saúde, confiança, circuit.

| Ação | Detalhe |
|------|---------|
| **Remover** | 1ª dobra Receitas/Despesas |
| **Mover** | Admin → Sistema → “Origem dos dados” (link discreto) |
| **Substituir** | Tooltip ℹ️ no KPI se dado stale (sem jargão) |

---

## 4. Labels em código vs UI

| Camada | Ação |
|--------|------|
| `frontend/services/*Engine.js` | Manter nomes internos — OK |
| `payload.*Engine` | Não renderizar nome do motor |
| CSS `.copilot-answer`, `.circuit-badge` | Renomear classes em refactor cosmético (opcional) |
| Colunas CSV “Learning”, “Engine” | Renomear export headers |

---

## 5. Mapa por macroárea

| Área | Linguagem executiva? | Pendências |
|------|---------------------|------------|
| Executivo | Parcial | Eliminar views engine |
| Financeiro | **Não** — banner snapshot | P0 |
| Combustíveis | Sim | — |
| Produtos | Parcial — “copilot” | Renomear sub-aba |
| Fiscal | Sim | Lineage só no detalhe com label amigável |
| Administração | Técnico permitido | Manter circuit/scheduler aqui |

---

## 6. Checklist implementação

- [ ] Remover banner resiliência executivo
- [ ] Eliminar 9 views com títulos engine (IA-1)
- [ ] Renomear 12 títulos (tabela §2)
- [ ] Fiscal: “Lineage Fiscal” → “Rastreabilidade de documentos”
- [ ] Nunca exibir `fromSnapshot`, `circuitStatus` na 1ª dobra
- [ ] Admin: manter diagnóstico completo

---

## 7. Classificação

| Critério | Status |
|----------|--------|
| Termos proibidos fora de Admin | **REPROVADO** (banner + órfãs) |
| Plano sem backend novo | **APROVADO** |
| Remove complexidade? | **SIM** |

---

**IA-5 — Conclusão:** Eliminar **telas engine** + **banner snapshot** + **renomear 12 títulos** = caminho para linguagem 100% executiva.
