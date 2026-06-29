---
# 💰 LOGOS IMPACT SCORE | LOGOS Architecture
# Type: ARCHITECTURE_SPEC
# Version: 1.0
# Sprint: PRODUCT-05 — LOGOS Impact System
# Status: SPECIFIED
---

# LOGOS Impact Score — Architecture

> **Sistema de mensuração do impacto financeiro gerado pelo LOGOS para o proprietário.**

---

## 🎯 Propósito

Responde a pergunta:

> **"Quanto dinheiro o LOGOS já gerou para este proprietário?"**

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    LOGOS IMPACT SCORE                        │
│                    Calculation Engine                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Recovered  │  │   Savings   │  │  Prevented  │        │
│  │  Calculator │  │  Calculator │  │  Calculator │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │               │
│         └────────────────┼────────────────┘               │
│                          │                                │
│                   ┌──────▼──────┐                         │
│                   │   Impact    │                         │
│                   │  Aggregator │                         │
│                   └──────┬──────┘                         │
│                          │                                │
│         ┌────────────────┼────────────────┐               │
│         ▼                ▼                ▼               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │    ROI      │  │    Time     │  │    Trend    │        │
│  │  Calculator │  │  Calculator │  │  Analyzer   │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │               │
│         └────────────────┼────────────────┘               │
│                          │                                │
│                   ┌──────▼──────┐                         │
│                   │  Impact     │                         │
│                   │   Score     │                         │
│                   │   Card      │                         │
│                   └─────────────┘                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Componentes

### 1. Recovered Calculator

**Responsabilidade:** Calcular dinheiro recuperado por ações do LOGOS.

#### Categorias de Recuperação

```python
class RecoveredCalculator:
    """Calculates money recovered through LOGOS decisions."""
    
    CATEGORIES = {
        'collections': {
            'description': 'Cobranças de clientes inadimplentes',
            'calculation': 'SUM(payments_received)',
            'validation': 'owner_confirmed',
        },
        'billing_corrections': {
            'description': 'Correções de erros de faturamento',
            'calculation': 'SUM(corrected_amounts)',
            'validation': 'invoice_comparison',
        },
        'reconciliation_gaps': {
            'description': 'Diferenças de reconciliação encontradas',
            'calculation': 'SUM(reconciled_amounts)',
            'validation': 'transaction_matching',
        },
        'duplicate_payments': {
            'description': 'Pagamentos duplicados identificados',
            'calculation': 'SUM(refunded_duplicates)',
            'validation': 'transaction_verification',
        },
    }
```

#### Exemplo de Cálculo

```json
{
  "recovered": {
    "collections": {
      "amount": 52000.00,
      "decisions": 12,
      "average_per_decision": 4333.33,
      "proof_ids": ["pay_001", "pay_002", "..."]
    },
    "billing_corrections": {
      "amount": 21300.00,
      "decisions": 5,
      "average_per_decision": 4260.00,
      "proof_ids": ["inv_001", "inv_002", "..."]
    },
    "reconciliation_gaps": {
      "amount": 14000.00,
      "decisions": 8,
      "average_per_decision": 1750.00,
      "proof_ids": ["rec_001", "rec_002", "..."]
    }
  },
  "total_recovered": 87300.00,
  "confidence": 0.94
}
```

---

### 2. Savings Calculator

**Responsabilidade:** Calcular economias obtidas em despesas.

#### Categorias de Economia

```python
class SavingsCalculator:
    """Calculates savings from expense optimizations."""
    
    CATEGORIES = {
        'negotiated_expenses': {
            'description': 'Despesas negociadas com desconto',
            'calculation': 'SUM(original_amount - paid_amount)',
            'validation': 'invoice_comparison',
        },
        'prevented_fees': {
            'description': 'Taxas e juros evitados',
            'calculation': 'SUM(fees_not_paid)',
            'validation': 'date_analysis',
        },
        'duplicate_cancellations': {
            'description': 'Duplicatas canceladas',
            'calculation': 'SUM(cancelled_amounts)',
            'validation': 'cancellation_proof',
        },
        'optimized_suppliers': {
            'description': 'Fornecedores mais baratos',
            'calculation': 'SUM(price_difference)',
            'validation': 'price_comparison',
        },
    }
```

#### Exemplo de Cálculo

```json
{
  "savings": {
    "negotiated_expenses": {
      "amount": 28000.00,
      "suppliers": ["Fornecedor A", "Fornecedor B"],
      "average_discount": 8.5
    },
    "prevented_fees": {
      "amount": 3200.00,
      "late_fees_avoided": 18,
      "average_fee": 177.78
    },
    "duplicate_cancellations": {
      "amount": 8200.00,
      "duplicates_found": 4
    },
    "optimized_suppliers": {
      "amount": 2000.00,
      "comparisons_made": 23
    }
  },
  "total_savings": 41400.00,
  "confidence": 0.91
}
```

---

### 3. Prevented Loss Calculator

**Responsabilidade:** Calcular perdas evitadas por detecção precoce.

#### Categorias de Prevenção

```python
class PreventedLossCalculator:
    """Calculates losses prevented through early detection."""
    
    CATEGORIES = {
        'sales_decline_prevented': {
            'description': 'Quedas de vendas detectadas e evitadas',
            'calculation': 'projected_loss - actual_loss',
            'validation': 'trend_analysis',
        },
        'margin_compression_prevented': {
            'description': 'Compressões de margem identificadas',
            'calculation': 'potential_loss - actual_loss',
            'validation': 'margin_tracking',
        },
        'stockout_prevented': {
            'description': 'Rupturas de estoque evitadas',
            'calculation': 'lost_sales_value',
            'validation': 'stock_alerts',
        },
        'fraud_prevented': {
            'description': 'Fraudes detectadas',
            'calculation': 'fraud_amount',
            'validation': 'anomaly_detection',
        },
    }
```

#### Exemplo de Cálculo

```json
{
  "prevented": {
    "sales_decline_prevented": {
      "amount": 18500.00,
      "detections": 3,
      "avg_response_time": "2.1 hours",
      "example": {
        "date": "2026-06-15",
        "decline_detected": "11.8%",
        "action_taken": "Price adjustment",
        "loss_prevented": 14200.00
      }
    },
    "margin_compression_prevented": {
      "amount": 8300.00,
      "compressions_detected": 4
    },
    "stockout_prevented": {
      "amount": 0.00,
      "alerts_sent": 2,
      "stockouts_prevented": 2
    }
  },
  "total_prevented": 26800.00,
  "confidence": 0.82,
  "note": "Prevented losses are estimates based on trend projections"
}
```

---

### 4. Additional Revenue Calculator

**Responsabilidade:** Calcular receitas adicionais capturadas.

#### Categorias de Receita Adicional

```python
class AdditionalRevenueCalculator:
    """Calculates additional revenue captured."""
    
    CATEGORIES = {
        'mix_optimization': {
            'description': 'Otimização de mix de produtos',
            'calculation': 'SUM(additional_sales)',
            'validation': 'sales_comparison',
        },
        'upsell_opportunities': {
            'description': 'Upsell de produtos premium',
            'calculation': 'SUM(premium_sales)',
            'validation': 'product_comparison',
        },
        'pricing_optimization': {
            'description': 'Ajustes de preço otimizados',
            'calculation': 'SUM(price_improvement)',
            'validation': 'price_analysis',
        },
        'demand_capture': {
            'description': 'Captura de demanda não atendida',
            'calculation': 'SUM(additional_volume × margin)',
            'validation': 'demand_analysis',
        },
    }
```

#### Exemplo de Cálculo

```json
{
  "additional": {
    "mix_optimization": {
      "amount": 9400.00,
      "shifts_recommended": 6,
      "shifts_executed": 5,
      "example": {
        "from": "Diesel S10",
        "to": "Gasolina Aditivada",
        "margin_improvement": "+12%",
        "additional_revenue": 2400.00
      }
    },
    "upsell_opportunities": {
      "amount": 6000.00,
      "premium_products": ["Aditivada", "Premium"]
    }
  },
  "total_additional": 15400.00,
  "confidence": 0.78
}
```

---

### 5. Time Saved Calculator

**Responsabilidade:** Calcular tempo economizado do proprietário.

```python
class TimeSavedCalculator:
    """Calculates time saved for the owner."""
    
    BASELINE_TIMES = {
        'manual_analysis': 30,      # minutes
        'report_generation': 15,    # minutes
        'data_consolidation': 20,   # minutes
        'decision_research': 45,    # minutes
    }
    
    def calculate_time_saved(self, decision_count, action_complexity):
        """Calculate time saved per decision type."""
        
        time_per_decision = {
            'collections': 20,      # Research + contact
            'expense_review': 15,   # Analysis
            'sales_investigation': 60, # Deep dive
            'opportunity_capture': 30, # Research + action
        }
        
        return decision_count × time_per_decision[action_complexity]
```

#### Exemplo de Cálculo

```json
{
  "time_saved": {
    "total_hours": 312,
    "total_days": 39,
    "breakdown": {
      "auto_detection": {
        "hours": 120,
        "description": "Detecção automática vs análise manual"
      },
      "context_preloading": {
        "hours": 85,
        "description": "Dados pré-carregados vs busca manual"
      },
      "prioritization": {
        "hours": 62,
        "description": "Priorização automática vs análise"
      },
      "quick_actions": {
        "hours": 45,
        "description": "Ações rápidas vs processos longos"
      }
    }
  },
  "monetary_value": {
    "owner_hourly_rate": 150.00,
    "total_value": 46800.00
  }
}
```

---

### 6. ROI Calculator

**Responsabilidade:** Calcular retorno sobre investimento.

```python
class ROICalculator:
    """Calculates return on investment."""
    
    def calculate_roi(
        self,
        total_impact: float,
        logos_cost: float,
        period_months: int
    ) -> dict:
        """Calculate various ROI metrics."""
        
        # Basic ROI
        roi_multiplier = total_impact / logos_cost
        
        # Percentage ROI
        roi_percentage = ((total_impact - logos_cost) / logos_cost) × 100
        
        # Annualized
        annualized_roi = roi_multiplier × (12 / period_months)
        
        # Monthly average
        monthly_impact = total_impact / period_months
        monthly_roi = monthly_impact / (logos_cost / period_months)
        
        return {
            'roi_multiplier': roi_multiplier,
            'roi_percentage': roi_percentage,
            'annualized_roi': annualized_roi,
            'monthly_impact': monthly_impact,
        }
```

#### Exemplo de Cálculo

```json
{
  "roi": {
    "logos_cost": {
      "monthly_subscription": 960.00,
      "total_period": 11520.00,
      "period_months": 12
    },
    "impact": {
      "recovered": 87300.00,
      "savings": 41400.00,
      "prevented": 26800.00,
      "additional": 15400.00,
      "total": 170900.00
    },
    "calculations": {
      "roi_multiplier": 14.83,
      "roi_percentage": 1383,
      "annualized_roi": 14.83,
      "monthly_impact": 14241.67,
      "monthly_roi": 14.83
    },
    "interpretation": "Cada R$ 1 investido no LOGOS gerou R$ 14.83 de retorno"
  }
}
```

---

## 📊 Data Model

### Impact Score Entity

```python
class LogosImpactScore(BaseModel):
    """Complete impact score for a tenant."""
    
    # Identification
    tenant_id: str
    empresa_codigo: str
    calculation_date: datetime
    period_start: date
    period_end: date
    
    # Financial Impact
    recovered: FinancialComponent
    savings: FinancialComponent
    prevented: FinancialComponent
    additional: FinancialComponent
    total_financial: float
    
    # Time Impact
    time_saved: TimeComponent
    time_monetary_value: float
    
    # ROI
    logos_cost: CostComponent
    roi_multiplier: float
    roi_percentage: float
    annualized_roi: float
    
    # Metadata
    confidence: float
    calculation_method: str
    verified_by_owner: bool
    last_updated: datetime


class FinancialComponent(BaseModel):
    """Financial impact component."""
    
    total: float
    categories: Dict[str, CategoryDetail]
    decision_count: int
    proof_ids: List[str]
    confidence: float


class TimeComponent(BaseModel):
    """Time impact component."""
    
    total_hours: float
    total_days: float
    categories: Dict[str, TimeCategory]
    hourly_rate: float
    monetary_value: float


class CostComponent(BaseModel):
    """LOGOS cost component."""
    
    monthly_subscription: float
    total_period: float
    period_months: int
    additional_costs: Optional[float] = 0
```

---

## 🔌 API Endpoints

### GET /api/v1/impact-score

**Descrição:** Retorna o LOGOS Impact Score completo.

**Parâmetros:**
- `tenant_id` (required)
- `period` (optional: 'month', 'quarter', 'year', 'all')

**Response:**
```json
{
  "tenant_id": "tenant_001",
  "calculation_date": "2026-06-29T20:00:00Z",
  "period": {
    "start": "2026-01-15",
    "end": "2026-06-29",
    "months": 5.5
  },
  "impact": {
    "recovered": {
      "total": 87300.00,
      "breakdown": {
        "collections": 52000.00,
        "billing_corrections": 21300.00,
        "reconciliation": 14000.00
      }
    },
    "savings": {
      "total": 41400.00,
      "breakdown": {
        "negotiated": 28000.00,
        "fees_prevented": 3200.00,
        "duplicates": 8200.00,
        "suppliers": 2000.00
      }
    },
    "prevented": {
      "total": 26800.00,
      "breakdown": {
        "sales_decline": 18500.00,
        "margin_compression": 8300.00
      },
      "note": "Estimates based on trend projections"
    },
    "additional": {
      "total": 15400.00,
      "breakdown": {
        "mix_optimization": 9400.00,
        "upsell": 6000.00
      }
    },
    "total": 170900.00
  },
  "time_saved": {
    "hours": 312,
    "days": 39,
    "monetary_value": 46800.00
  },
  "roi": {
    "multiplier": 14.83,
    "percentage": 1383,
    "monthly_average": 14.83
  },
  "confidence": 0.89
}
```

### POST /api/v1/impact-score/verify

**Descrição:** Owner confirma ou ajusta valores calculados.

**Request:**
```json
{
  "component": "recovered",
  "category": "collections",
  "verified_amount": 52000.00,
  "verification_proof": "bank_statement_001"
}
```

---

## 🔄 Integration Points

### Entrada

```
Decision History ──► Impact Calculators ──► Impact Score
Execution Results       (5 calculators)
```

### Saída

```
Impact Score ──► Dashboard
           ├───► Reports
           ├───► Gamification
           └───► Billing Justification
```

---

## ✅ Validation Rules

| Component | Validation | Confidence |
|-----------|------------|------------|
| Recovered | Owner confirmation / Bank statement | ≥ 0.90 |
| Savings | Invoice comparison | ≥ 0.85 |
| Prevented | Trend analysis / Projections | ≥ 0.75 |
| Additional | Sales comparison | ≥ 0.80 |
| Time | Decision count × Baseline | ≥ 0.85 |
| ROI | (Recovered + Savings + Additional) / Cost | ≥ 0.90 |

---

## 📚 Referências

- [LOGOS_IMPACT_SYSTEM.md](../business/LOGOS_IMPACT_SYSTEM.md) — Visão do sistema
- [DECISION_EFFECTIVENESS.md](../business/DECISION_EFFECTIVENESS.md) — Métricas de eficácia

---

**[LOGOS IMPACT SCORE — Architecture]**

*Status: SPECIFIED | Components: 6 | Confidence: 89% | ROI Target: > 10x*
