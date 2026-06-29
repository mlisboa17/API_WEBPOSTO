---
# 🔍 SALES INVESTIGATION ENGINE | LOGOS
# Type: ARCHITECTURE_SPEC
# Version: 1.0
# Sprint: PRODUCT-04 — Owner Operating System
# Status: SPECIFIED
---

# Sales Investigation Engine

> **Quando detectar qualquer queda nas vendas, investigar automaticamente.**
>
> **Jamais informar apenas: "As vendas caíram."**

---

## 🎯 Propósito

Transformar alertas de queda de vendas em **investigações completas** com:

- Causa raiz identificada
- Impacto financeiro quantificado  
- Recomendações acionáveis
- Confidence Score

---

## 📋 Regra de Ouro

```
❌ PROIBIDO:
   "As vendas caíram 11,8%."

✅ OBRIGATÓRIO:
   "As vendas caíram 11,8%.
   
   87% da perda ocorreu no Diesel S10 
   entre 18h e 22h no POSTO VIP.
   
   Impacto estimado: R$ 14.280.
   
   Recomendação:
   Verificar preço, estoque e concorrência."
```

---

## 🔬 Investigation Dimensions

### 1. PRODUTO (Product Dimension)

**Descobrir automaticamente:**

| Combustível | Código | Análise |
|-------------|--------|---------|
| Gasolina Comum | GASOLINA_COMUM | Volume, margem, ticket |
| Gasolina Aditivada | GASOLINA_ADITIVADA | Volume, margem, ticket |
| Etanol | ETANOL | Volume, margem, ticket |
| Etanol Aditivado | ETANOL_ADITIVADO | Volume, margem, ticket |
| Diesel Comum | DIESEL_COMUM | Volume, margem, ticket |
| Diesel S10 | DIESEL_S10 | Volume, margem, ticket |
| Diesel Aditivado | DIESEL_ADITIVADO | Volume, margem, ticket |
| GNV | GNV | Volume, margem, ticket |
| Outros | AUTO_DISCOVERED | Detectados automaticamente |

**Análise por produto:**
- Volume (litros) vs baseline
- Margem (R$/L) vs baseline
- Ticket médio vs baseline
- Quantidade de transações vs baseline
- Share do mix vs baseline

### 2. LOCALIZAÇÃO (Location Dimension)

**Identificar:**

| Nível | Descrição |
|-------|-----------|
| **Posto** | Qual empresa/filial |
| **Turno** | Manhã/Tarde/Noite/Madrugada |
| **Dia** | Dia específico da semana |
| **Horário** | Hora específica (granularidade 1h) |

**Análise temporal:**
- Heatmap de vendas por hora
- Comparação dia-a-dia
- Sazonalidade (mesmo dia semana anterior)

### 3. CAUSAS POTENCIAIS (Root Cause Analysis)

#### 3.1 Perda de Litros
```
Cálculo:
Litros Perdidos = (Baseline Litros - Atual Litros) × Preço Médio

Investigar:
• Estoque disponível (stockout?)
• Bomba funcionando?
• Preço vs concorrência
```

#### 3.2 Perda de Margem
```
Cálculo:
Margem Perdida = (Baseline Margem - Atual Margem) × Litros Vendidos

Investigar:
• Preço de compra aumentou?
• Descontos concedidos?
• Mix shift para produtos de menor margem?
```

#### 3.3 Perda de Ticket
```
Cálculo:
Ticket Perdido = (Baseline Ticket - Atual Ticket) × Quantidade Transações

Investigar:
• Clientes comprando menos litros?
• Produtos premium sendo substituídos?
• Promoções concorrentes?
```

#### 3.4 Perda de Clientes
```
Cálculo:
Clientes Perdidos = Baseline Count - Atual Count

Investigar:
• Quantidade de transações caiu?
• Clientes novos diminuíram?
• Clientes recorrentes pararam de vir?
```

#### 3.5 Alteração do Mix
```
Análise:
• Gasolina vs Etanol ratio mudou?
• Premium vs Regular ratio mudou?
• Novos produtos sendo adotados?
```

#### 3.6 Correlações

**Com despesas:**
```
Correlação: Vendas ↓ quando Despesas ↑ ?
Possível causa: Investimento em marketing reduziu?
```

**Com cartões:**
```
Correlação: Vendas ↓ quando Cartão % ↑ ?
Possível causa: Problemas de processamento?
```

**Com PIX:**
```
Correlação: Vendas ↓ quando PIX % ↓ ?
Possível causa: Sistema de PIX fora do ar?
```

**Com estoque:**
```
Correlação: Vendas ↓ quando Estoque < nível crítico ?
Possível causa: Stockout de produto popular?
```

**Com funcionários:**
```
Correlação: Vendas ↓ quando Funcionários no turno < baseline ?
Possível causa: Falta de atendentes no horário de pico?
```

---

## 📊 Investigation Output Format

### Template de Resposta

```json
{
  "investigation_id": "inv_001_20260629",
  "alert_type": "sales_decline",
  "detected_at": "2026-06-29T08:00:00Z",
  "investigated_at": "2026-06-29T08:00:15Z",
  
  "summary": {
    "headline": "Vendas caíram 11,8%",
    "primary_contributor": "Diesel S10",
    "contribution_percent": 87,
    "location": "POSTO VIP",
    "time_window": "18h-22h",
    "estimated_impact": 14280.00
  },
  
  "breakdown": {
    "by_product": [
      {
        "product": "Diesel S10",
        "decline_percent": 23.5,
        "contribution_to_total": 87,
        "volume_loss_liters": 450.5,
        "revenue_loss": 10575.00,
        "margin_loss": 1586.25
      },
      {
        "product": "Gasolina Comum",
        "decline_percent": 5.2,
        "contribution_to_total": 10,
        "volume_loss_liters": 89.2,
        "revenue_loss": 2100.00,
        "margin_loss": 315.00
      }
    ],
    
    "by_time": {
      "peak_impact_hours": ["18:00", "19:00", "20:00", "21:00"],
      "shift": "noite",
      "day_pattern": "quinta-feira (mesmo dia semana anterior: normal)"
    },
    
    "by_location": {
      "primary_posto": "POSTO VIP (11495)",
      "comparison_with_others": "OUTROS POSTOS: estáveis"
    }
  },
  
  "root_cause_analysis": {
    "probable_causes": [
      {
        "cause": "preço_acima_concorrencia",
        "confidence": 0.75,
        "evidence": "Preço Diesel S10 3% acima da média regional",
        "impact_estimate": 8000.00
      },
      {
        "cause": "estoque_baixo",
        "confidence": 0.60,
        "evidence": "Estoque Diesel S10 em 12% (crítico < 15%)",
        "impact_estimate": 4000.00
      },
      {
        "cause": "funcionarios_ausentes",
        "confidence": 0.45,
        "evidence": "2 funcionários a menos no turno da noite",
        "impact_estimate": 2280.00
      }
    ],
    
    "investigation_depth": "full",
    "investigation_confidence": 0.89
  },
  
  "financial_impact": {
    "revenue_loss_daily": 14280.00,
    "revenue_loss_projected_monthly": 428400.00,
    "profit_loss_daily": 2142.00,
    "profit_loss_projected_monthly": 64260.00,
    "margin_loss_percent": 2.3,
    "recovery_potential": 12000.00
  },
  
  "recommendations": {
    "immediate": [
      {
        "action": "Verificar preço Diesel S10 vs concorrência",
        "priority": "critical",
        "time_to_execute": "15 minutos",
        "expected_impact": 8000.00
      },
      {
        "action": "Solicitar reposição urgente de Diesel S10",
        "priority": "high",
        "time_to_execute": "30 minutos",
        "expected_impact": 4000.00
      }
    ],
    "short_term": [
      {
        "action": "Revisar escala do turno da noite",
        "priority": "medium",
        "time_to_execute": "1 dia",
        "expected_impact": 2000.00
      }
    ],
    "monitoring": [
      "Acompanhar vendas Diesel S10 a cada 2h",
      "Monitorar nível de estoque",
      "Verificar preços concorrentes 2x ao dia"
    ]
  },
  
  "decision": {
    "decision_id": "dec_inv_001",
    "title": "Investigar queda de 11,8% nas vendas — R$ 14.280 em risco",
    "description": "Vendas caíram 11,8%. 87% da perda ocorreu no Diesel S10 entre 18h-22h. Investigar preço, estoque e escala.",
    "financial_impact": 14280.00,
    "confidence": 0.89,
    "priority": "critical",
    "suggested_actions": [
      "Verificar preço Diesel S10 vs concorrência",
      "Solicitar reposição urgente de Diesel S10",
      "Revisar escala do turno da noite"
    ]
  }
}
```

---

## 🔄 Investigation Process

```
┌─────────────────────────────────────────────────────────────┐
│  1. DETECÇÃO                                               │
│     • Alerta: Vendas caíram X% vs baseline                 │
│     • Threshold: > 10% decline                           │
│     • Trigger: Real-time ou batch analysis                 │
└────────────────┬──────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  2. TRIAGEM                                                │
│     • É significativo? (> R$ 5.000 impacto)                │
│     • É persistente? (> 2 dias consecutivos)               │
│     • Investigar ou apenas monitorar?                      │
└────────────────┬──────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  3. INVESTIGAÇÃO DE PRODUTO                                │
│     • Que produtos caíram?                                 │
│     • Qual a contribuição de cada um?                      │
│     • Ranking por impacto financeiro                         │
└────────────────┬──────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  4. INVESTIGAÇÃO TEMPORAL                                  │
│     • Em qual horário?                                     │
│     • Em qual turno?                                       │
│     • Dia específico ou padrão?                            │
└────────────────┬──────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  5. INVESTIGAÇÃO DE CAUSAS                                 │
│     • Litros, Margem, Ticket, Clientes?                  │
│     • Correlações: Estoque, Funcionários, Preço?           │
│     • Identificar causa raiz provável                      │
└────────────────┬──────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  6. CÁLCULO DE IMPACTO                                     │
│     • Receita perdida                                      │
│     • Lucro perdido                                        │
│     • Projeção mensal                                      │
│     • Potencial de recuperação                             │
└────────────────┬──────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  7. GERAÇÃO DE DECISÃO                                     │
│     • Criar DailyDecision                                  │
│     • Priorizar no Top 5                                   │
│     • Incluir no Owner Action Center                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Implementation Strategy

### Phase 1: Basic Investigation (MVP)
- Detect sales decline > 10%
- Identify primary product contributor
- Calculate financial impact
- Generate basic recommendation

### Phase 2: Dimensional Analysis
- Add time dimension (hour/shift/day)
- Add location dimension (posto comparison)
- Add product breakdown (all fuels)

### Phase 3: Root Cause Detection
- Correlate with stock levels
- Correlate with staff presence
- Compare with competitor prices (if available)
- Identify most probable cause

### Phase 4: Advanced Analytics
- Machine learning for pattern recognition
- Predictive alerts (before decline happens)
- Automated recommendations with confidence

---

## 📁 Files

| File | Purpose |
|------|---------|
| `sales_investigation_engine.py` | Core engine |
| `product_analyzer.py` | Product dimension analysis |
| `temporal_analyzer.py` | Time dimension analysis |
| `correlation_engine.py` | Cross-factor correlation |
| `impact_calculator.py` | Financial impact estimation |
| `recommendation_generator.py` | Action recommendations |

---

## ✅ Success Criteria

| Metric | Target |
|--------|--------|
| Investigation completeness | 100% (all 6 dimensions) |
| Root cause accuracy | > 70% (validated) |
| Time to investigate | < 30 seconds |
| False positive rate | < 10% |
| Owner satisfaction | > 80% (survey) |

---

**[SALES INVESTIGATION ENGINE — PRODUCT-04]**

*Status: SPECIFIED | Implementation: PENDING | Priority: HIGH*
