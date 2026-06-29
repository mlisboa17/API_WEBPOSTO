---
# 🏗️ OWNER INTELLIGENCE ENGINE | LOGOS
# Type: ARCHITECTURE
# Version: 1.0
# Sprint: PRODUCT-03 — Owner Action Center
# Status: IMPLEMENTED
---

# Owner Intelligence Engine — Architecture

> Core decision engine for the LOGOS Owner Action Center.
> Transforms data into decisions through 4 specialized motors.

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   OWNER INTELLIGENCE ENGINE                      │
│                    (Orchestrator)                                │
└──────────────────┬──────────────────────────────────────────────┘
                   │
       ┌───────────┼───────────┬───────────┐
       │           │           │           │
       ▼           ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  Motor 1 │ │  Motor 2 │ │  Motor 3 │ │  Motor 4 │
│  Money   │ │  Recover │ │  Growth  │ │  Daily   │
│  at Risk │ │  Money   │ │  Opp     │ │  Actions │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │            │
     └────────────┴────────────┴────────────┘
                  │
                  ▼
        ┌─────────────────┐
        │ Priority Engine │
        │  (Scoring)      │
        └────────┬────────┘
                 │
                 ▼
     ┌─────────────────────────────┐
     │ OwnerActionCenterSummary    │
     │  • Business Health          │
     │  • Money at Risk            │
     │  • Recoverable Money        │
     │  • Opportunities            │
     │  • Top 5 Decisions          │
     └─────────────────────────────┘
```

---

## 🏗️ Module Structure

```
src/services/owner_intelligence/
├── __init__.py                    # Public API exports
├── schemas.py                     # Pydantic models (50+ classes)
├── money_at_risk.py               # Motor 1: Risk detection
├── recoverable_money.py           # Motor 2: Recovery detection
├── growth_opportunities.py        # Motor 3: Opportunity discovery
├── daily_actions.py               # Motor 4: Decision generation
├── priority_engine.py             # Scoring algorithm
└── owner_intelligence_engine.py   # Main orchestrator
```

---

## 🔧 Motor 1 — Money At Risk Engine

### Responsibility
Detect financial threats and potential losses.

### Risk Types Detected

| Risk Type | Detection Method | Threshold |
|-----------|------------------|-------------|
| `revenue_decline` | Baseline comparison | > 20% below |
| `expense_increase` | Baseline comparison | > 30% above |
| `cash_shortage` | Cash position | < -R$ 1.000 |
| `margin_compression` | Margin vs baseline | > 5% drop |
| `voucher_anomaly` | Voucher vs baseline | > 50% increase |
| `overdue_receivables` | AR aging | Any overdue |
| `card_reconciliation` | Card balance diff | > R$ 500 |

### Baseline Calculation

```python
def _calculate_baseline(values: List[float]) -> float:
    """Statistical baseline with outlier removal."""
    
    # 1. Calculate mean
    mean = sum(values) / len(values)
    
    # 2. Calculate std deviation
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std_dev = variance ** 0.5
    
    # 3. Remove outliers (Z-score > 2.0)
    filtered = [x for x in values if abs((x - mean) / std_dev) < 2.0]
    
    # 4. Return mean of filtered
    return sum(filtered) / len(filtered)
```

### Configuration

```python
BaselineConfig(
    lookback_days=30,      # Days for baseline
    min_data_points=7,     # Minimum for statistical validity
    outlier_threshold=2.0,  # Z-score threshold
    seasonal_adjustment=True  # Adjust for day of week
)

RiskThresholds(
    revenue_drop_percent=20.0,
    expense_increase_percent=30.0,
    cash_shortage_threshold=1000.0,
    margin_drop_percent=5.0,
    overdue_days=7
)
```

---

## 🔧 Motor 2 — Recoverable Money Engine

### Responsibility
Find recoverable funds and missed revenue opportunities.

### Recovery Types

| Type | Description | Recovery Probability |
|------|-------------|----------------------|
| `overdue_receivable` | Customer payments overdue | 80% (<30d), 60% (>30d) |
| `unbilled_sale` | Sales not invoiced | 95% |
| `card_reconciliation_gap` | Card settlement pending | 90% |
| `duplicate_payment` | Accidental duplicate | 70% |
| `billing_error` | Under-billing | 85% |
| `unclaimed_credit` | Supplier credits | 90% |
| `negotiable_expense` | Renegotiable contracts | 50% |

### Expected Value Calculation

```
Expected Recovery = Amount × Recovery Probability

Example:
- Overdue: R$ 10,000 × 80% = R$ 8,000 expected
- Unbilled: R$ 5,000 × 95% = R$ 4,750 expected
- Duplicate: R$ 2,000 × 70% = R$ 1,400 expected
Total: R$ 14,150 expected recovery
```

---

## 🔧 Motor 3 — Growth Opportunities Engine

### Responsibility
Discover growth and optimization opportunities.

### Opportunity Types

| Type | Discovery Method | Value Estimation |
|------|------------------|------------------|
| `product_trend` | Volume growth > 40% | 20% more volume |
| `market_share_loss` | Decline > 25% | Recovery value |
| `mix_optimization` | Premium % < 15% | Upsell margin |
| `payment_trend` | Pix growth > 50% | Fee reduction |
| `premium_opportunity` | Low premium mix | Margin gain |
| `pattern_optimization` | Day variation > 40% | Weak day boost |
| `margin_improvement` | Low margin < 5% | Price adjustment |

### Trend Detection

```python
def detect_trend(current: float, baseline: float) -> Dict:
    """Detect and characterize trends."""
    
    change_pct = ((current - baseline) / baseline) * 100
    
    if change_pct >= 40:
        return {
            "direction": "up",
            "strength": min(change_pct / 100, 1.0),
            "type": "strong_growth"
        }
    elif change_pct <= -25:
        return {
            "direction": "down",
            "strength": abs(change_pct) / 100,
            "type": "significant_decline"
        }
    else:
        return {
            "direction": "stable",
            "strength": 0.3,
            "type": "normal_variation"
        }
```

---

## 🔧 Motor 4 — Daily Actions Engine

### Responsibility
Generate prioritized daily decisions from all findings.

### Decision Generation Pipeline

```
┌─────────────────────────────────────────────────────────┐
│ Input: Findings from Motors 1, 2, 3                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 1. Convert Findings → Decision Candidates               │
│    • Calculate financial value (expected)                 │
│    • Determine urgency (0-1)                            │
│    • Extract confidence                                 │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Score with Priority Engine                         │
│    • Financial Impact (30%)                             │
│    • Urgency (25%)                                      │
│    • Confidence (20%)                                   │
│    • Ease (15%)                                         │
│    • Time (10%)                                         │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Rank by Total Score                                  │
│    • Sort descending                                    │
│    • Assign ranks                                       │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Filter by Confidence                                 │
│    • Minimum: 60%                                       │
│    • Display threshold: 80%                             │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Generate Top 5 + All Decisions                        │
│    • Create DailyDecision objects                       │
│    • Generate explanations (why, what, how)             │
│    • Create executive summary                           │
└─────────────────────────────────────────────────────────┘
```

### Decision Structure

```python
class DailyDecision:
    # Identification
    id: str
    rank: int  # 1-5 for top, 6+ for others
    
    # Content
    title: str  # Max 100 chars
    description: str  # Max 500 chars
    decision_question: str  # Owner-facing question
    
    # Explanations (6 Ws)
    why_appeared: str
    why_ranked: str
    money_involved: str
    what_rule_triggered: str
    
    # Scoring
    total_score: float  # 0-100
    financial_impact_score: float
    urgency_score: float
    confidence_score: float
    ease_score: float
    time_score: float
    
    # Action
    action: DecisionAction  # Executable action
    
    # Metadata
    decision_type: str  # "risk", "recovery", "opportunity"
    related_findings: List[str]
```

---

## ⚖️ Priority Engine

### Scoring Algorithm

```python
class PriorityEngine:
    """Calculates priority scores for decisions."""
    
    WEIGHTS = {
        "financial_impact": 0.30,
        "urgency": 0.25,
        "confidence": 0.20,
        "ease": 0.15,
        "time": 0.10
    }
    
    def calculate_score(
        self,
        financial_value: float,
        urgency_score: float,
        confidence: float,
        action_type: ActionType,
        priority: ActionPriority,
        time_to_resolve: Optional[int]
    ) -> Dict[str, float]:
        
        # Component scores
        financial_score = self._score_financial(financial_value)
        urgency_component = self._score_urgency(urgency_score, priority, action_type)
        confidence_component = self._score_confidence(confidence)
        ease_score = self._score_ease(time_to_resolve)
        time_score = self._score_time(time_to_resolve)
        
        # Weighted total
        total = (
            financial_score * WEIGHTS["financial_impact"] +
            urgency_component * WEIGHTS["urgency"] +
            confidence_component * WEIGHTS["confidence"] +
            ease_score * WEIGHTS["ease"] +
            time_score * WEIGHTS["time"]
        )
        
        # Apply priority multipliers
        total = self._apply_multipliers(total, priority, action_type)
        
        return {
            "total_score": min(100, total),
            "financial_impact_score": financial_score,
            "urgency_score": urgency_component,
            "confidence_score": confidence_component,
            "ease_score": ease_score,
            "time_score": time_score
        }
```

### Financial Impact Scoring

| Value (R$) | Score |
|------------|-------|
| > 100.000 | 100 |
| 50.000 - 100.000 | 90 |
| 20.000 - 50.000 | 80 |
| 10.000 - 20.000 | 70 |
| 5.000 - 10.000 | 60 |
| 2.000 - 5.000 | 50 |
| 1.000 - 2.000 | 40 |
| 500 - 1.000 | 30 |
| 100 - 500 | 20 |
| < 100 | 10 |

---

## 🔀 Main Orchestrator

### OwnerIntelligenceEngine

```python
class OwnerIntelligenceEngine:
    """Core orchestrator coordinating all motors."""
    
    def __init__(self):
        self.money_at_risk_engine = MoneyAtRiskEngine()
        self.recoverable_money_engine = RecoverableMoneyEngine()
        self.growth_opportunities_engine = GrowthOpportunitiesEngine()
        self.daily_actions_engine = DailyActionsEngine()
    
    async def generate_action_center_summary(
        self,
        tenant_id: str,
        empresa_codigo: str,
        data_sources: EngineDataSources
    ) -> OwnerActionCenterSummary:
        
        # 1. Run Motor 1
        money_at_risk = await self.money_at_risk_engine.analyze(...)
        
        # 2. Run Motor 2
        recoverable_money = await self.recoverable_money_engine.analyze(...)
        
        # 3. Run Motor 3
        opportunities = await self.growth_opportunities_engine.analyze(...)
        
        # 4. Calculate Business Health
        business_health = self._calculate_business_health(...)
        
        # 5. Run Motor 4
        top_5, all_decisions = await self.daily_actions_engine.generate_decisions(...)
        
        # 6. Assemble Summary
        return OwnerActionCenterSummary(
            tenant_id=tenant_id,
            empresa_codigo=empresa_codigo,
            business_health=business_health,
            money_at_risk=money_at_risk,
            recoverable_money=recoverable_money,
            opportunities=opportunities,
            top_5_decisions=top_5,
            all_decisions=all_decisions,
            ...
        )
```

---

## 📊 Data Flow

```
┌──────────────────────────────────────────────────────────┐
│  Data Sources (Existing Services)                         │
│  • Financial Overview                                     │
│  • Accounts Receivable                                    │
│  • Accounts Payable                                     │
│  • Sales Data                                           │
│  • Product Data                                         │
│  • Payment Data                                         │
│  • Card Data                                            │
│  • Expense Data                                         │
│  • Historical Data                                      │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  EngineDataSources (Aggregator)                         │
│  Validates and structures data for motors                │
└────────────────────┬─────────────────────────────────────┘
                     │
       ┌─────────────┼─────────────┐
       │             │             │
       ▼             ▼             ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Motor 1  │  │ Motor 2  │  │ Motor 3  │
│ Risks    │  │ Recovery │  │ Growth   │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │
     └─────────────┴─────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────┐
│  Motor 4: DailyActionsEngine                            │
│  • Score candidates                                      │
│  • Rank decisions                                        │
│  • Generate explanations                                 │
└────────────────────┬───────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  OwnerActionCenterSummary                                 │
│  Complete output for frontend                           │
└──────────────────────────────────────────────────────────┘
```

---

## 🔒 Trust & Traceability

### Every Decision Includes

```python
class DecisionSource:
    endpoint: str           # API endpoint used
    service: str            # Service name
    method: str            # Detection method/rule
    data_timestamp: datetime  # When data was fetched
    parameters: Dict       # Query parameters

class DecisionAction:
    # ... action fields ...
    confidence: float      # 0-1 confidence score
    confidence_level: ConfidenceLevel  # very_high, high, medium, low
    source: DecisionSource # Full traceability
```

### Confidence Levels

| Level | Score Range | Display |
|-------|-------------|---------|
| Very High | 90-100% | ✅ Solid |
| High | 80-89% | ✅ Good |
| Medium | 60-79% | ⚠️ Review |
| Low | < 60% | ❌ Hide |

---

## 🧪 Testing Strategy

### Unit Tests

```python
# Test MoneyAtRiskEngine
def test_revenue_decline_detection():
    engine = MoneyAtRiskEngine()
    financial_data = {"total_revenue": 8000}  # 20% below baseline
    historical = {"revenues": [10000, 9500, 11000, ...]}
    
    findings = await engine.analyze(...)
    
    assert len(findings) == 1
    assert findings[0].risk_type == "revenue_decline"
    assert findings[0].deviation_percent <= -20

# Test PriorityEngine
def test_priority_calculation():
    engine = PriorityEngine()
    
    scores = engine.calculate_score(
        financial_value=50000,
        urgency_score=0.8,
        confidence=0.85,
        action_type=ActionType.URGENT,
        priority=ActionPriority.CRITICAL,
        time_to_resolve=30
    )
    
    assert scores["total_score"] > 80
    assert scores["financial_impact_score"] == 60  # 50k = 60 pts
```

### Integration Tests

```python
async def test_full_pipeline():
    engine = OwnerIntelligenceEngine()
    
    summary = await engine.generate_action_center_summary(
        tenant_id="test_tenant",
        empresa_codigo="12345",
        data_sources=mock_data_sources()
    )
    
    assert summary.tenant_id == "test_tenant"
    assert len(summary.top_5_decisions) <= 5
    assert summary.business_health.score >= 0
    assert summary.confidence_average >= 0
```

---

## 📈 Performance Targets

| Metric | Target |
|--------|--------|
| End-to-end latency | < 2 seconds |
| Motor 1 execution | < 500ms |
| Motor 2 execution | < 500ms |
| Motor 3 execution | < 500ms |
| Motor 4 execution | < 300ms |
| Concurrent requests | 100/sec |
| Memory per request | < 100MB |

---

## 🚀 Future Enhancements

### Short Term
- [ ] Cache TTL for baseline calculations
- [ ] More risk detectors (fraud, theft patterns)
- [ ] SMS/Email notifications for critical decisions
- [ ] Decision execution tracking

### Medium Term
- [ ] Machine learning for baseline predictions
- [ ] Predictive risk modeling
- [ ] Natural language explanations (GPT integration)
- [ ] Mobile push notifications

### Long Term
- [ ] Cross-tenant benchmarking (anonymized)
- [ ] Industry trend integration
- [ ] Autonomous action execution (with approval)
- [ ] Voice interface for quick decisions

---

**[OWNER INTELLIGENCE ENGINE — PRODUCT-03]**

*Status: IMPLEMENTED | Motors: 4/4 COMPLETE | API: COMPLETE | Tests: PENDING*
