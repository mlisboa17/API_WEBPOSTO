---
# 📝 DECISION_LOG.md | LOGOS
# Type: DECISION_LOG
# Version: 1.1
# Updated: 2026-06-29
---

# LOGOS — Decision Log

> **Registro formal de todas as decisões arquiteturais e de produto**

---

## ADR-022: Decision Execution Platform
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** EXEC-01

### Contexto
O LOGOS detecta decisões mas não acompanha execução e resultado. Uma decisão só tem valor quando executada e medida.

### Decisão
- Criar Decision Execution Platform com 9 estados
- Separar estritamente: Estimado (projeção) vs Confirmado (fato)
- Todas as transições com timestamp e audit trail
- Confirmação obrigatória: SIM/PARCIAL/NÃO
- Impacto confirmado requer evidência

### Implementação
- DecisionStatusMachine: 9 estados, 11 transições
- ExecutionService: orquestração
- ResultConfirmation: confirmação com rastreabilidade
- Strict separation: EstimatedImpact vs ConfirmedImpact

### Consequências
- ✅ Decisões completamente rastreáveis
- ✅ Honestidade técnica: nunca misturar estimado e confirmado
- ✅ Valor comprovado apenas com evidência
- ⚠️ Complexidade de implementação
- ⚠️ Requer mudança de comportamento do usuário

---

## ADR-023: Strict Separation of Estimated vs Confirmed Impact
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** EXEC-01

### Contexto
Risco de apresentar projeções como fatos, gerando expectativas incorretas.

### Decisão
- ALWAYS label estimated as "ESTIMADO"
- NEVER show confirmed without verification_method
- NEVER mix estimated and confirmed in same calculation
- ALWAYS calculate and display variance
- Display labels are MANDATORY and cannot be removed

### UX Rules
```
ESTIMADO: R$ 20.000     ← Always show
CONFIRMADO: R$ 18.450    ← Only after confirmation
Variância: -7.75%        ← Always calculate
```

### Consequências
- ✅ Transparência absoluta com proprietário
- ✅ Aprendizado de variância
- ✅ Honestidade técnica inquestionável
- ⚠️ UI mais complexa (dois números vs um)
- ⚠️ Possível percepção de "erro" se variância alta

---

## ADR-024: Mandatory Result Confirmation
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** EXEC-01

### Contexto
Sem confirmação, não sabemos se decisão gerou valor real.

### Decisão
- Toda execução DEVE ter confirmação
- Opções: SIM / PARCIALMENTE / NÃO
- Se SIM: valor confirmado obrigatório
- Se PARCIAL: progresso e motivo
- Se NÃO: motivo da rejeição
- Nenhuma exceção

### States
```
EXECUTING → COMPLETED (confirmation.result == YES)
EXECUTING → NOT_COMPLETED (confirmation.result == NO)
EXECUTING → PARTIAL (confirmation.result == PARTIAL)
```

### Consequências
- ✅ Dados de eficácia completos
- ✅ Aprendizado contínuo
- ✅ Accountability do sistema
- ⚠️ Fricção para usuário
- ⚠️ Requer mudança de hábito

---

## 📊 Resumo por Status

| Status | Quantidade |
|--------|------------|
| ✅ ACCEPTED | 13 |
| 🔄 PROPOSED | 11 |
| ⚠️ DEPRECATED | 0 |
| 🔄 SUPERSEDED | 0 |
| **Total** | **24** |

---

## 🔗 Referências

- [PRODUCT_CONSTITUTION.md](../business/PRODUCT_CONSTITUTION.md) — Princípios do produto
- [ROADMAP.md](../business/ROADMAP.md) — Evolução das fases
- [SPRINT_HISTORY.md](SPRINT_HISTORY.md) — Histórico de sprints

---

**[DECISION_LOG — LOGOS Architecture Decisions]**

*Decisions: 24 | Accepted: 13 | Proposed: 11 | Last Updated: 2026-06-29*
