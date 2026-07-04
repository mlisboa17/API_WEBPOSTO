---
# 📝 DECISION_LOG.md | LOGOS
# Type: DECISION_LOG
# Version: 1.2
# Updated: 2026-06-29
---

# LOGOS — Decision Log

> **Registro formal de todas as decisões arquiteturais e de produto**

---

## ADR-024: Expense Loss Detector (VALUE-03)
**Status:** ✅ ACCEPTED  
**Data:** 2026-07-04  
**Sprint:** VALUE-03

### Contexto
LOGOS precisava responder "onde estou perdendo dinheiro" em despesas, não apenas combustível.

### Decisão
- Fonte: `CONSULTAR_DESPESAS_FINANCEIRO_REDE` + `TITULO_PAGAR`
- Baseline adaptativo 30d vs 30d anterior
- Money Found sempre ESTIMATED; duplicidade = POSSÍVEL DUPLICIDADE
- Detector compete com FuelRevenueDetector no Discovery Engine

### Evidência
- `docs/validation/VALUE_03_EXPENSE_DATA_RAW.json`
- `docs/validation/VALUE_03_DISCOVERY_RAW.json`
- `docs/governance/PCG_VALUE_03.md` (96/100)

---

## ADR-023: Fast Daily Analysis Loop + Single-Flight por Scope
**Status:** ✅ ACCEPTED  
**Data:** 2026-07-04  
**Sprint:** PERFORMANCE-01

### Contexto
Home bloqueava ~205s na análise multi-tenant. Prompt 3 introduziu cache/concurrency; single-flight falhou sob POST concurrente (2 analysis_id).

### Decisão
- Snapshot imediato + refresh background (`OwnerAnalysisSnapshotService`)
- Fuel cache em `snapshots/discovery_fuel` com chave tenant+empresa+período
- `OWNER_ANALYSIS_MAX_CONCURRENCY=3` por evidência runtime
- Single-flight: lock `asyncio` por scope + reserva atômica antes de `create_task`

### Evidência
- `docs/runtime/PERFORMANCE_01_RUNTIME_REPORT.md`
- `docs/performance/PERFORMANCE_01_SINGLE_FLIGHT_RAW.json`

---
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

## ADR-025: Momento Zero — 10-Second Clarity
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** UX-01

### Contexto
A Home do LOGOS estava se tornando complexa, com múltiplos widgets, gráficos, tabelas. O proprietário gastava muito tempo procurando informação.

### Decisão
- Redesenhar a Home para clareza imediata em ≤10 segundos
- Uma tela, sem scroll, sem widgets secundários
- Top 3 decisões + ação imediata
- Business Health discreto (não protagonista)
- LOGOS Impact separando estimado vs confirmado
- Protocolo oficial: "Ten Second Rule"

### Implementação
- MOMENTO_ZERO_UX.md: especificação completa
- TEN_SECOND_RULE.md: protocolo de teste
- HOME_INFORMATION_ARCHITECTURE.md: estrutura lógica
- DESIGN_SYSTEM_V4.md: tokens atualizados

### Consequências
- ✅ Clareza imediata
- ✅ Experiência premium
- ✅ Redução de fricção cognitiva
- ✅ Foco em decisões, não em dados
- ⚠️ Requer implementação Next.js completa
- ⚠️ Mudança drástica na UX atual

---

## ADR-026: Princípio 18 — Clareza acima de Complexidade
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** UX-01

### Contexto
A Product Constitution tinha 17 princípios focados em dados, decisões e impacto, mas nenhum sobre UX e clareza.

### Decisão
Adicionar Princípio 18: "O proprietário deve entender a tela principal em menos de 10 segundos. Qualquer elemento que não contribua diretamente para uma decisão deve ser removido."

### Implementação
- Atualizar PRODUCT_CONSTITUTION.md para versão 5.0
- Adicionar Princípio 18 com:
  - Declaração
  - Rule of thumb
  - Exemplos de aplicação
  - Checklist
  - Consequências de violação

### Consequências
- ✅ Formalizaço da clareza como princípio obrigatório
- ✅ Critério objetivo para simplificação de interfaces
- ✅ Alinhamento com "Momento Zero"
- ✅ Garantia de experiência premium
- ⚠️ Requer revisão de todas as telas futuras

---

## ADR-027: Daily Ritual Concept
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** UX-01

### Contexto
O LOGOS era apenas uma ferramenta. Queríamos transformá-lo em parte do ritual diário do proprietário.

### Decisão
- Definir "Daily Ritual" com 3 momentos: manhã (preparar), tarde (check-in), noite (fechar dia)
- Mensagem "Dia Concluído" ao final
- Sensação de progresso diário
- Notificações inteligentes

### Implementação
- DAILY_RITUAL.md: conceito completo
- MOMENTO_ZERO_UX.md: greeting + closure messages
- EXECUTIVE_EXPERIENCE.md: microinterações para ritual

### Consequências
- ✅ LOGOS como parte da rotina
- ✅ Engagement aumentado
- ✅ Sensação de progresso e closure
- ⚠️ Depende de notificações inteligentes
- ⚠️ Requer implementação de scheduling

---

## ADR-028: Design System V4 — Premium Executive Experience
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** UX-01

### Contexto
O Design System V3 estava funcional, mas não transmitia experiência premium de produto executivo.

### Decisão
- Atualizar para Design System V4 com:
  - Semantic color tokens (light/dark)
  - Tipografia modular (Inter/JetBrains Mono)
  - Espaçamento 8px-based
  - Shadows/elevations premium
  - Microinterações discretas
  - Dark mode como first-class citizen
- Inspiração: Apple, Stripe, Linear, Arc, Raycast, Vercel

### Implementação
- DESIGN_SYSTEM_V4.md: tokens completos
- EXECUTIVE_EXPERIENCE.md: princípios de design
- HOME_INFORMATION_ARCHITECTURE.md: aplicação prática

### Consequências
- ✅ Experiência visualmente premium
- ✅ Consistência entre light/dark
- ✅ Performance percebida (animações otimizadas)
- ✅ Acessibilidade (WCAG AA)
- ⚠️ Requer refatoração de componentes existentes
- ⚠️ Curva de aprendizado para implementadores

---

## 📊 Resumo por Status

| Status | Quantidade |
|--------|------------|
| ✅ ACCEPTED | 13 |
| 🔄 PROPOSED | 15 |
| ⚠️ DEPRECATED | 0 |
| 🔄 SUPERSEDED | 0 |
| **Total** | **28** |

---

## 🔗 Referências

- [PRODUCT_CONSTITUTION.md](../business/PRODUCT_CONSTITUTION.md) — Princípios do produto
- [ROADMAP.md](../business/ROADMAP.md) — Evolução das fases
- [SPRINT_HISTORY.md](SPRINT_HISTORY.md) — Histórico de sprints

---

**[DECISION_LOG — LOGOS Architecture Decisions]**

*Decisions: 28 | Accepted: 13 | Proposed: 15 | Last Updated: 2026-06-29*
