---
# 🚀 DECISION EXECUTION PLATFORM | LOGOS
# Type: PRODUCT_SPEC
# Version: 1.0
# Sprint: EXEC-01 — Decision Execution Platform
# Status: IMPLEMENTED
---

# Decision Execution Platform

> **"Uma decisão não termina quando aparece na tela. Ela termina quando foi detectada, investigada, explicada, executada, confirmada, medida e aprendida."**

---

## 🎯 Visão

Até hoje o LOGOS **detecta**.

Agora ele deve **acompanhar**.

Uma decisão só terá valor quando existir evidência de que foi **executada** e qual **resultado produziu**.

---

## 🔄 Ciclo Completo de Execução

```
┌─────────────┐
│  DETECTADA  │  ← Motor detecta anomalia/oportunidade
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ INVESTIGADA │  ← Sales Investigation Engine analisa
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  EXPLICADA  │  ← Decision Explainer traduz para owner
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  EXECUTADA  │  ← Owner clica "Executar Agora"
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  CONFIRMADA │  ← Owner confirma resultado
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    MEDIDA   │  ← Impacto financeiro registrado
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   APRENDIDA │  ← Alimenta algoritmos de aprendizado
└─────────────┘
```

---

## 📊 Decision Status Machine

### Estados Oficiais

| Estado | Descrição | Transições Válidas |
|--------|-----------|-------------------|
| **NEW** | Decisão criada, aguardando apresentação | → READY, → CANCELLED |
| **READY** | Apresentada ao proprietário, aguardando execução | → EXECUTING, → EXPIRED, → CANCELLED |
| **EXECUTING** | Proprietário iniciou execução | → COMPLETED, → NOT_COMPLETED, → PARTIAL |
| **COMPLETED** | Ação executada com sucesso | → ARCHIVED |
| **NOT_COMPLETED** | Ação não foi executada | → ARCHIVED |
| **PARTIAL** | Ação executada parcialmente | → ARCHIVED |
| **EXPIRED** | Expirou (> 7 dias sem ação) | → ARCHIVED |
| **CANCELLED** | Cancelada antes da execução | → ARCHIVED |
| **ARCHIVED** | Arquivada após estado terminal | — |

### Fluxo de Estados

```
NEW ──► READY ──► EXECUTING ──► COMPLETED ──► ARCHIVED
              │         │
              │         ├──► NOT_COMPLETED ──► ARCHIVED
              │         │
              │         └──► PARTIAL ──► ARCHIVED
              │
              ├──► EXPIRED ──► ARCHIVED
              │
              └──► CANCELLED ──► ARCHIVED
```

### Transições Automáticas

- **EXPIRED**: Após 7 dias em READY sem ação
- **ARCHIVED**: Terminal states após 30 dias (7 dias para EXPIRED/CANCELLED)

### Timestamps Obrigatórios

Cada transição registra:
- Timestamp UTC
- Actor (system | user | auto)
- Ação executada
- Metadata (user_id, reason, etc.)

---

## ▶️ Decision Execution

### Botão Principal

Cada decisão possui um botão principal de ação:

| Tipo de Decisão | Botão | Ação |
|----------------|-------|------|
| Cobrança | **Cobrar** | Abre tela de cobrança com cliente pré-selecionado |
| Negociação | **Negociar** | Abre contato/cadastro do fornecedor |
| Investigação | **Investigar** | Abre análise de queda com dados pre-carregados |
| Despesa | **Abrir Despesa** | Abre lançamento com campos sugeridos |
| Reconciliação | **Ver Cartões** | Abre reconciliação de cartões pendentes |
| Estoque | **Ver Estoque** | Mostra nível de estoque do produto identificado |
| Genérico | **Executar Agora** | Ação padrão com contexto carregado |

### Contexto Pré-Carregado

**É PROIBIDO:** Obrigar o usuário a procurar informações manualmente.

**É OBRIGATÓRIO:** Carregar automaticamente:
- IDs relevantes (cliente, fatura, fornecedor)
- Valores pré-preenchidos
- Contexto da decisão
- Deep link para tela correta

### Exemplo: Cobrar Cliente

```
Decisão: "Cobrar cliente inadimplente"
Valor: R$ 8.500

[Executar Agora] →

┌────────────────────────────────────┐
│  Cobrança                        │
│                                   │
│  Cliente: ABC Ltda              │  ← Pré-carregado
│  CNPJ: 12.345.678/0001-90       │  ← Pré-carregado
│  Valor: R$ 8.500,00             │  ← Pré-carregado
│  Vencimento: 15/06/2026          │  ← Pré-carregado
│  Fatura: #INV-2026-001234        │  ← Pré-carregado
│                                   │
│  [Gerar Boleto] [Enviar Email]  │
│  [Registrar Ligação]             │
│                                   │
│  Último contato: Nunca          │  ← Contexto
│                                   │
└────────────────────────────────────┘
```

---

## ✅ Result Confirmation

### Pergunta Obrigatória

Após execução, o sistema pergunta automaticamente:

> **"A decisão resolveu o problema?"**

### Opções

| Opção | Descrição | Quando Usar |
|-------|-----------|-------------|
| **SIM** | Decisão resolveu completamente | Ação executada com sucesso |
| **PARCIALMENTE** | Decisão resolveu parcialmente | Ação em progresso ou resultado parcial |
| **NÃO** | Decisão não resolveu | Ação não executada ou falhou |

### Se SIM

Registra:
- ✅ Valor recuperado/economizado/adicional
- ✅ Método de verificação
- ✅ IDs de evidências
- ✅ Tempo gasto
- ✅ Notas opcionais

### Se PARCIALMENTE

Registra:
- ◐ Progresso percentual (0-100%)
- ◐ Motivo do parcial
- ◐ Detalhes
- ◐ Próxima ação recomendada
- ◐ Valor confirmado (se houver)

### Se NÃO

Registra:
- ❌ Motivo da rejeição
  - Não era prioridade
  - Não tinha tempo
  - Informação incorreta
  - Já resolvido de outra forma
  - Não conseguiu contato
  - Bloqueio externo
  - Outro
- ❌ Detalhes adicionais
- ❌ Permite nova investigação

---

## 📊 Separação Estrita: Estimado vs Confirmado

### PROIBIDO (Antes)

```
❌ ERRADO:
┌────────────────────────────────────┐
│  IMPACTO: R$ 20.000               │  ← Estimado ou confirmado?
└────────────────────────────────────┘
```

### OBRIGATÓRIO (Depois)

```
✅ CERTO:
┌────────────────────────────────────┐
│  💰 IMPACTO FINANCEIRO            │
├────────────────────────────────────┤
│                                   │
│  ESTIMADO:      R$ 20.000         │
│    ↓                              │
│  CONFIRMADO:    R$ 18.450 (92%)   │
│                                   │
│  Variância:     -7.75%            │
│                                   │
│  [Ver Detalhes →]                 │
│                                   │
└────────────────────────────────────┘
```

### Regras

| Regra | Aplicação |
|-------|-----------|
| **Sempre separar** | Nunca misturar estimado e confirmado |
| **Sempre marcar** | Cada valor deve ter label claro |
| **Confirmado = Fato** | Só mostrar confirmado após verificação |
| **Estimado = Projeção** | Sempre mostrar como projeção |
| **Variance = Aprendizado** | Calcular e exibir diferença |

### Estados do Valor

| Estado | Label | Quando Mostrar |
|--------|-------|----------------|
| **Estimado** | "ESTIMADO" | Antes da execução |
| **Confirmado** | "CONFIRMADO" | Após confirmação SIM |
| **Parcial** | "PARCIALMENTE CONFIRMADO" | Após confirmação PARCIAL |
| **Em Validação** | "EM VALIDAÇÃO" | Durante execução |

---

## 📈 Decision Timeline

### Eventos Registrados

Cada decisão mantém timeline completa:

```
┌─────────────────────────────────────────────────────────────┐
│  TIMELINE — Decisão #DEC-001                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  08:10:00  ● Detectada                                      │
│            Motor: MoneyAtRisk                               │
│            Anomalia: Cliente inadimplente > 30 dias        │
│                                                             │
│  08:11:00  ● Investigada                                    │
│            Causa: Fatura #INV-2026-001234 vencida          │
│            Impacto estimado: R$ 8.500                       │
│                                                             │
│  08:12:00  ● Explicada                                      │
│            Título: Cobrar cliente inadimplente              │
│            Ação: Gerar boleto e enviar email                │
│            Apresentada a: João Silva                        │
│                                                             │
│  09:05:00  ● Executada                                      │
│            Usuário: João Silva                              │
│            Ação: Clique em "Cobrar"                       │
│            Contexto carregado: Cliente ABC Ltda           │
│                                                             │
│  09:12:00  ● Confirmada                                    │
│            Resultado: SIM                                   │
│            Valor confirmado: R$ 8.500                      │
│            Verificação: Comprovante PIX                     │
│            Evidência: #EVID-789                            │
│            Tempo gasto: 7 minutos                         │
│                                                             │
│  09:13:00  ● Medida                                        │
│            Impacto registrado: +R$ 8.500                   │
│            LOGOS Impact Score atualizado                  │
│                                                             │
│  09:14:00  ● Aprendida                                     │
│            Padrão: Cobrança direta = alta eficácia          │
│            Modelo atualizado                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Campos do Evento

- `event_id`: UUID único
- `timestamp`: UTC
- `status`: Estado após transição
- `actor`: Quem/what (system | user | auto)
- `action`: Descrição da ação
- `metadata`: Contexto adicional

---

## 📊 Execution Metrics

### Métricas Calculadas

| Métrica | Descrição | Fórmula |
|---------|-----------|---------|
| **Decisões Geradas** | Total criadas no período | Count |
| **Taxa de Apresentação** | % apresentadas | Presented / Generated × 100 |
| **Taxa de Execução** | % executadas | Executed / Presented × 100 |
| **Taxa de Conclusão** | % concluídas com sucesso | Completed / Executed × 100 |
| **Taxa de Sucesso** | % SIM ou PARCIAL | (Completed + Partial) / Executed × 100 |
| **Tempo até Execução** | Média de READY → EXECUTING | AVG(timestamp_executing - timestamp_ready) |
| **Tempo de Resolução** | Média de EXECUTING → terminal | AVG(timestamp_terminal - timestamp_executing) |
| **Impacto Estimado** | Soma de todas as projeções | SUM(estimated) |
| **Impacto Confirmado** | Soma de valores verificados | SUM(confirmed) |
| **Taxa de Confirmação** | % do estimado que foi confirmado | Confirmed / Estimated × 100 |

### Dashboard de Métricas

```
┌─────────────────────────────────────────────────────────────┐
│  📊 EXECUTION METRICS — Junho/2026                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  VOLUME                                                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  Geradas: 42                                                  │
│  Apresentadas: 42 (100%)                                     │
│  Executadas: 38 (90%)                                        │
│  Concluídas: 35 (92%)                                        │
│                                                             │
│  TEMPO                                                        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  Média até execução: 4.2 horas                               │
│  Média de resolução: 7 minutos                               │
│                                                             │
│  IMPACTO                                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  Estimado:          R$ 125.000                              │
│  Confirmado:        R$ 118.000 (94%)                         │
│  Em Validação:      R$ 7.000                                │
│                                                             │
│  Variância média:   -5.6%                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔒 Honestidade Técnica (Obrigatório)

### É PROIBIDO

- ❌ Exibir ROI baseado apenas em projeções
- ❌ Exibir dinheiro recuperado sem confirmação
- ❌ Exibir economia sem evidência
- ❌ Misturar impacto estimado com impacto confirmado
- ❌ Apresentar métricas sem rastreabilidade

### É OBRIGATÓRIO

- ✅ Toda informação financeira informar sua origem
- ✅ Estimado, Confirmado ou Em Validação
- ✅ Rastreabilidade completa (decisão → execução → confirmação)

### Origem do Valor

| Tipo | Origem | Exemplo |
|------|--------|---------|
| **Estimado** | `source_engine` + `calculation_method` | "Estimado por MoneyAtRiskEngine usando baseline histórico" |
| **Confirmado** | `verification_method` + `evidence_ids` | "Confirmado por owner via comprovante PIX #PIX-789" |
| **Em Validação** | `execution_timestamp` + `pending_reason` | "Aguardando confirmação do owner desde 2026-06-29T09:05:00Z" |

---

## 🏗️ Arquitetura

### Componentes

```
┌─────────────────────────────────────────────────────────────┐
│              DECISION EXECUTION PLATFORM                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │          Decision Status Machine                     │   │
│  │  • State transitions                               │   │
│  │  • Validation rules                                │   │
│  │  • Auto expiration/archival                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│          ┌────────────────┼────────────────┐              │
│          ▼                ▼                ▼              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │  Execution   │ │   Result     │ │   Timeline   │      │
│  │   Service    │ │ Confirmation │ │   Manager    │      │
│  └──────────────┘ └──────────────┘ └──────────────┘      │
│          │                │                │              │
│          └────────────────┼────────────────┘              │
│                           │                               │
│                   ┌───────▼────────┐                      │
│                   │   Metrics      │                      │
│                   │  Calculator    │                      │
│                   └───────────────┘                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Models (Pydantic)

| Model | Propósito |
|-------|-----------|
| `ExecutionRecord` | Registro completo de execução |
| `ResultConfirmation` | Confirmação do resultado |
| `ExecutionTimeline` | Timeline de eventos |
| `TimelineEvent` | Evento individual |
| `EstimatedImpact` | Impacto projetado (estimativa) |
| `ConfirmedImpact` | Impacto verificado (fato) |

### Services

| Service | Responsabilidade |
|---------|------------------|
| `DecisionStatusMachine` | Gerenciamento de estados |
| `ExecutionService` | Orquestração de execução |
| `MetricsCalculator` | Cálculo de métricas |

---

## 📋 API Endpoints (Propostos)

### POST /api/v1/decisions/{id}/execute
Inicia execução de decisão.

### POST /api/v1/decisions/{id}/confirm
Confirma resultado da execução.

### GET /api/v1/decisions/{id}/timeline
Retorna timeline completa.

### GET /api/v1/execution-metrics
Retorna métricas de execução.

### GET /api/v1/execution-summary
Retorna resumo para dashboard.

---

## ✅ Checklist de Implementação

### Backend

- [x] Decision Status Machine
- [x] Status transitions com timestamps
- [x] Auto-expiration (7 dias)
- [x] Auto-archival (30 dias)
- [x] Execution Service
- [x] Result Confirmation (SIM/PARCIAL/NÃO)
- [x] Timeline tracking
- [x] Impact separation (estimated vs confirmed)
- [x] Metrics Calculator
- [ ] Persistência (repository)
- [ ] API endpoints
- [ ] Webhook para notificações

### Frontend

- [ ] Botões de execução
- [ ] Tela de confirmação
- [ ] Timeline visual
- [ ] Dashboard de métricas
- [ ] Indicadores de estado
- [ ] Labels ESTIMADO/CONFIRMADO

### Integração

- [ ] Integração com Owner Intelligence Engine
- [ ] Integração com LOGOS Impact Score
- [ ] Integração com Decision History

---

**[DECISION EXECUTION PLATFORM — EXEC-01]**

*Status: IMPLEMENTED | Backend: ✅ | Frontend: ⏳ | Integration: ⏳*
