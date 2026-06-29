---
# 🔄 DECISION EXECUTION FLOW | LOGOS
# Type: PROCESS_SPEC
# Version: 1.0
# Sprint: PRODUCT-05 — LOGOS Impact System
# Status: DEFINED
---

# Decision Execution Flow

> **Ciclo completo: Detectar → Investigar → Explicar → Executar → Confirmar → Medir → Aprender**
>
> Não poderão existir decisões sem acompanhamento.

---

## 🔄 Ciclo Completo

```
        ┌──────────────┐
        │   DETECTAR   │ ◄──────┐
        └──────┬───────┘        │
               │                │
               ▼                │
        ┌──────────────┐         │
        │ INVESTIGAR   │         │
        └──────┬───────┘         │
               │                 │
               ▼                 │
        ┌──────────────┐         │
        │   EXPLICAR   │         │
        └──────┬───────┘         │
               │                 │
               ▼                 │
        ┌──────────────┐         │
        │   EXECUTAR   │         │
        └──────┬───────┘         │
               │                 │
               ▼                 │
        ┌──────────────┐         │
        │  CONFIRMAR   │         │
        └──────┬───────┘         │
               │                 │
               ▼                 │
        ┌──────────────┐         │
        │    MEDIR     │         │
        └──────┬───────┘         │
               │                 │
               ▼                 │
        ┌──────────────┐         │
        │   APRENDER   │─────────┘
        └──────────────┘   (feedback loop)
```

---

## 1️⃣ DETECTAR

### Objetivo
Identificar anomalias, riscos e oportunidades nos dados.

### Como Funciona
- **5 Motores** do Owner Action Center analisam continuamente
- **Thresholds automáticos** baseados em baselines históricos
- **Confidence Score** calculado para cada detecção

### Responsável
```
┌─────────────────────────────────────────┐
│  Money At Risk Engine                  │
│  Recoverable Money Engine              │
│  Growth Opportunities Engine           │
│  Daily Actions Engine                  │
│  Sales Investigation Engine            │
└─────────────────────────────────────────┘
```

### Output
```json
{
  "detection_id": "det_001",
  "type": "sales_decline",
  "severity": "high",
  "confidence": 0.87,
  "summary": "Vendas caíram 11.8%",
  "estimated_impact": 14280.00,
  "timestamp": "2026-06-29T08:00:00Z"
}
```

---

## 2️⃣ INVESTIGAR

### Objetivo
Analisar a causa raiz do problema identificado.

### Como Funciona
- **Sales Investigation Engine** dispara automaticamente
- **6 dimensões** de análise: produto, local, tempo, métricas, causas, impacto
- **Correlações** com outros dados (estoque, funcionários, preços)

### Responsável
```
┌─────────────────────────────────────────┐
│  Sales Investigation Engine            │
│  ├── Product Analyzer                  │
│  ├── Temporal Analyzer                 │
│  ├── Correlation Engine                │
│  └── Impact Calculator                 │
└─────────────────────────────────────────┘
```

### Output
```json
{
  "investigation_id": "inv_001",
  "detection_id": "det_001",
  "findings": {
    "primary_product": "DIESEL_S10",
    "contribution": 0.87,
    "time_window": "18h-22h",
    "location": "POSTO_VIP",
    "probable_causes": [
      {
        "cause": "price_above_competition",
        "confidence": 0.75,
        "evidence": "Price 3% above regional avg"
      },
      {
        "cause": "low_stock",
        "confidence": 0.60,
        "evidence": "Stock at 12% (critical < 15%)"
      }
    ]
  },
  "calculated_impact": {
    "revenue_loss": 14280.00,
    "profit_loss": 2142.00,
    "recovery_potential": 12000.00
  }
}
```

---

## 3️⃣ EXPLICAR

### Objetivo
Traduzir a investigação técnica em linguagem do proprietário.

### Como Funciona
- **Decision Explainer** (6 perguntas)
- **Natural language generation**
- **Contexto financeiro** sempre incluído

### Responsável
```
┌─────────────────────────────────────────┐
│  Decision Explainer                    │
│  └── 6 Questions:                      │
│      1. Why this decision appeared?     │
│      2. How much money is involved?     │
│      3. How much can I gain?            │
│      4. How much can I lose?            │
│      5. How long does it take?          │
│      6. What action should I take?      │
└─────────────────────────────────────────┘
```

### Output
```
┌─────────────────────────────────────────┐
│  DECISÃO #1                              │
│                                          │
│  Investigar queda de 11.8% nas vendas    │
│                                          │
│  Por que apareceu:                       │
│  → Vendas caíram 11.8% acima do baseline│
│                                          │
│  Quanto dinheiro envolve:                │
│  → R$ 14.280 em receita em risco         │
│                                          │
│  Quanto posso perder se não agir:        │
│  → R$ 2.142 de lucro até o fim do mês    │
│                                          │
│  Quanto tempo leva:                      │
│  → 15 minutos para verificar preço       │
│                                          │
│  O que fazer:                            │
│  → Verificar preço do Diesel S10        │
│  → Conferir nível de estoque             │
│  → Comparar com concorrência            │
│                                          │
│  [Executar Agora →]                      │
└─────────────────────────────────────────┘
```

---

## 4️⃣ EXECUTAR

### Objetivo
Realizar a ação recomendada.

### Tipos de Execução

#### Ação Direta (In-app)
```
Cenário: Cobrar cliente inadimplente

┌─────────────────────────────────────────┐
│  [Executar Agora]                      │
│         ↓                              │
│  ┌─────────────────────────────────┐   │
│  │  Tela de Cobrança               │   │
│  │                                 │   │
│  │  Cliente: ABC Ltda              │   │
│  │  Valor: R$ 8.500                │   │
│  │  Vencimento: 15/06/2026        │   │
│  │                                 │   │
│  │  [Gerar Boleto] [Enviar Email]  │   │
│  │  [Registrar Ligação]            │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

#### Ação Externa (Redirect)
```
Cenário: Verificar preço da concorrência

┌─────────────────────────────────────────┐
│  [Executar Agora]                      │
│         ↓                              │
│  Abre app de anotações com:            │
│  - Localização do posto                │
│  - Produto: Diesel S10                 │
│  - Preço atual: R$ 4.89                │
│  - Espaço para anotar concorrência     │
└─────────────────────────────────────────┘
```

### Responsável
```
┌─────────────────────────────────────────┐
│  Execution Router                        │
│  ├── In-app Action Handler              │
│  ├── External Link Generator            │
│  └── Context Pre-loader                 │
└─────────────────────────────────────────┘
```

---

## 5️⃣ CONFIRMAR

### Objetivo
Registrar o resultado da execução.

### Fluxo

#### SIM — Executada
```
┌─────────────────────────────────────────┐
│  ✅ RESULTADO                            │
│                                          │
│  A decisão foi executada?              │
│                                          │
│  [✓ SIM]    [✗ NÃO]    [◐ PARCIAL]      │
│         ↓                                │
│  Qual o resultado?                       │
│  [R$ ____] [Confirmar]                  │
│                                          │
│  ⭐ Conquista: Executor de Decisões!     │
└─────────────────────────────────────────┘
```

#### NÃO — Não Executada
```
┌─────────────────────────────────────────┐
│  ❌ RESULTADO                            │
│                                          │
│  Qual o motivo?                          │
│                                          │
│  ○ Não era prioridade                   │
│  ○ Não tinha tempo                      │
│  ○ Informação incorreta                 │
│  ○ Já resolvido de outra forma          │
│  ○ Não consegui contato                 │
│  ○ Outro: _________                     │
│                                          │
│  [Continuar]                            │
└─────────────────────────────────────────┘
```

#### PARCIALMENTE
```
┌─────────────────────────────────────────┐
│  ◐ RESULTADO PARCIAL                     │
│                                          │
│  Progresso: [██████░░░░] 60%            │
│                                          │
│  Próximo passo:                         │
│  Aguardar retorno do cliente            │
│                                          │
│  [Agendar Lembrete]                     │
└─────────────────────────────────────────┘
```

### Responsável
```
┌─────────────────────────────────────────┐
│  Confirmation Handler                    │
│  ├── Result Capture                     │
│  ├── Motivation Logger                  │
│  └── Achievement System                 │
└─────────────────────────────────────────┘
```

---

## 6️⃣ MEDIR

### Objetivo
Quantificar o impacto financeiro real.

### Como Funciona
- **Before/after comparison**
- **Owner confirmation** do valor
- **Automatic calculation** quando possível

### Métricas

| Tipo | Cálculo | Exemplo |
|------|---------|---------|
| **Recuperado** | Valor recebido após cobrança | R$ 8.500 |
| **Economizado** | Diferença de despesa | R$ 3.200 |
| **Evitado** | Prejuízo que não ocorreu | R$ 14.200 |
| **Adicional** | Receita extra capturada | R$ 6.800 |
| **Tempo** | Horas economizadas | 2.5h |

### Output
```json
{
  "measurement_id": "mes_001",
  "decision_id": "dec_001",
  "execution_id": "exec_001",
  "measured_impact": {
    "financial": {
      "recovered": 8500.00,
      "currency": "BRL"
    },
    "time_saved": {
      "hours": 2.5,
      "description": "Auto-detection vs manual analysis"
    },
    "calculation_method": "owner_confirmed",
    "confidence": 0.95
  },
  "timestamp": "2026-06-29T10:30:00Z"
}
```

---

## 7️⃣ APRENDER

### Objetivo
Alimentar algoritmos com resultados para melhorar futuras decisões.

### Como Funciona
- **Machine learning models** atualizados
- **Pattern recognition** de sucesso/falha
- **Owner behavior analysis**

### O Que Aprendemos

#### Por Decisão
```
Tipo: "sales_decline_diesel"
├─ Ação recomendada: "Verificar preço"
├─ Taxa de execução: 85%
├─ Taxa de sucesso: 72%
├─ Tempo médio: 2.3 dias
└─ Valor médio recuperado: R$ 12.400

→ Próxima vez: Prioridade +5, Confiança +10%
```

#### Por Proprietário
```
Proprietário: João Silva
├─ Executa decisões de: Segunda e Quinta
├─ Prefere: Ações rápidas (< 30 min)
├─ Melhor horário: 8h-9h da manhã
├─ Ignora: Decisões < R$ 1.000
└─ Top categoria: Cobranças

→ Próximas decisões: Priorizar cobranças,
                     Agendar para Seg/Quinta,
                     Enviar às 8h
```

### Responsável
```
┌─────────────────────────────────────────┐
│  Learning Engine                         │
│  ├── Decision Success Model             │
│  ├── Owner Behavior Analysis            │
│  ├── Recommendation Optimizer           │
│  └── Baseline Refiner                   │
└─────────────────────────────────────────┘
```

---

## 📊 Estado de uma Decisão

```
┌─────────────────────────────────────────┐
│  STATES                                 │
│                                          │
│  DETECTED ──► INVESTIGATING            │
│                  │                       │
│                  ▼                       │
│              EXPLAINED ──► PENDING       │
│                              │           │
│                              ▼           │
│                          EXECUTED ──► CONFIRMED
│                                          │
│                                          ▼
│                                      MEASURED
│                                          │
│                                          ▼
│                                      LEARNED ✓
│                                          │
│              ┌───────────────────────────┘
│              │
│              ▼
│  CANCELLED ◄─┘ (a qualquer momento)
│  EXPIRED   ◄─┘ (após 7 dias sem ação)
└─────────────────────────────────────────┘
```

---

## ⏱️ Timeline Típica

| Fase | Tempo | Acumulado |
|------|-------|-----------|
| **Detectar** | < 1 min | 1 min |
| **Investigar** | 1-5 min | 6 min |
| **Explicar** | < 1s | 6 min |
| **Executar** | 5-30 min | 36 min |
| **Confirmar** | < 1 min | 37 min |
| **Medir** | 1-7 dias | 7 dias |
| **Aprender** | Contínuo | — |

---

## 🔗 Integração com Sistemas

### Entrada
```
WebPosto API ──► Detection Engine ──► Decision Pipeline
```

### Saída
```
Decision Pipeline ──► Execution Router ──► Action Handler
                         │
                         ├─► In-app Module
                         ├─► Email Service
                         ├─► SMS Service
                         └─► Calendar Integration
```

### Feedback
```
Owner Action ──► Confirmation Handler ──► Learning Engine
                                              │
                                              ▼
                                         Decision Optimizer
```

---

## ✅ Checklist de Implementação

### Detectar
- [ ] 5 motores operacionais
- [ ] Confidence Score calculado
- [ ] Thresholds automáticos

### Investigar
- [ ] Sales Investigation Engine ativo
- [ ] 6 dimensões cobertas
- [ ] Correlações implementadas

### Explicar
- [ ] 6 perguntas respondidas
- [ ] Linguagem natural gerada
- [ ] Contexto financeiro incluído

### Executar
- [ ] Botão "Executar Agora" funcional
- [ ] Contexto pré-carregado
- [ ] Ações diretas e externas

### Confirmar
- [ ] Fluxo SIM/NÃO/PARCIAL
- [ ] Motivos de não-execução
- [ ] Gamificação (conquistas)

### Medir
- [ ] Impacto financeiro calculado
- [ ] Confirmação do owner
- [ ] Atualização do Impact Score

### Aprender
- [ ] Modelos ML atualizados
- [ ] Behavior analysis rodando
- [ ] Recomendações otimizadas

---

## 📚 Referências

- [LOGOS_IMPACT_SYSTEM.md](LOGOS_IMPACT_SYSTEM.md) — Visão do sistema
- [MOMENTO_ZERO.md](MOMENTO_ZERO.md) — Conceito dos 10 segundos
- [DECISION_EFFECTIVENESS.md](DECISION_EFFECTIVENESS.md) — Métricas de eficácia

---

**[DECISION EXECUTION FLOW — PRODUCT-05]**

*Status: DEFINED | Cycle: 7 phases | Tracking: Complete | Learning: Enabled*
