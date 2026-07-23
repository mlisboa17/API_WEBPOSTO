"""
Owner Intelligence Schemas

Pydantic models for the Owner Action Center.
Defines the structure for decisions, findings, and actions.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ActionType(str, Enum):
    """Types of actions the owner can take."""

    URGENT = "urgent"  # Immediate action required
    RECOVER = "recover"  # Recover money/revenue
    OPTIMIZE = "optimize"  # Improve efficiency/profit
    REVIEW = "review"  # Review and decide
    MONITOR = "monitor"  # Keep monitoring


class ActionPriority(str, Enum):
    """Priority levels for actions."""

    CRITICAL = "critical"  # Act now, major impact
    HIGH = "high"  # Act today, significant impact
    MEDIUM = "medium"  # Act this week, moderate impact
    LOW = "low"  # Act when possible, minor impact


class ActionStatus(str, Enum):
    """Status of an action/decision."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class ConfidenceLevel(str, Enum):
    """Confidence levels for findings."""

    VERY_HIGH = "very_high"  # > 90%
    HIGH = "high"  # 80-90%
    MEDIUM = "medium"  # 60-80%
    LOW = "low"  # < 60%


class FinancialImpact(BaseModel):
    """Financial impact of a decision or finding."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"estimated_value": 5000.0, "currency": "BRL", "impact_type": "recoverable"}
            ]
        }
    )

    estimated_value: float = Field(..., description="Estimated financial value in BRL")
    currency: str = Field(default="BRL", description="Currency code")
    impact_type: str = Field(
        ..., description="Type: loss_prevented, recoverable, gain_opportunity, cost_avoidance"
    )
    probability: float = Field(
        ..., ge=0, le=1, description="Probability of achieving this impact (0-1)"
    )
    timeframe_days: int = Field(..., description="Expected timeframe to realize this impact")

    @property
    def expected_value(self) -> float:
        """Calculate expected value (value × probability)."""
        return self.estimated_value * self.probability


class DecisionSource(BaseModel):
    """Source information for a decision."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "endpoint": "/v1/financial/overview",
                    "service": "FinancialOverviewService",
                    "data_timestamp": "2026-06-29T10:00:00Z",
                }
            ]
        }
    )

    endpoint: str = Field(..., description="API endpoint that provided the data")
    service: str = Field(..., description="Service name that generated the finding")
    method: Optional[str] = Field(default=None, description="Method/rule that triggered this")
    data_timestamp: datetime = Field(..., description="When the source data was collected")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Parameters used in the query"
    )


class DecisionAction(BaseModel):
    """A specific action the owner should take."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "act_001",
                    "title": "Review overdue accounts",
                    "description": "3 accounts totaling R$ 12,450 are overdue. Contact customers immediately.",
                }
            ]
        }
    )

    id: str = Field(..., description="Unique action identifier")
    type: ActionType = Field(..., description="Type of action")
    priority: ActionPriority = Field(..., description="Priority level")
    status: ActionStatus = Field(default=ActionStatus.PENDING)

    # Content
    title: str = Field(..., max_length=100, description="Short, actionable title")
    description: str = Field(..., max_length=500, description="Clear description of what to do")
    context: Optional[str] = Field(default=None, description="Additional context for the decision")

    # Financial
    financial_impact: FinancialImpact = Field(..., description="Expected financial impact")

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None, description="When this action expires")
    time_to_resolve: Optional[int] = Field(default=None, description="Estimated minutes to resolve")

    # Source & Trust
    source: DecisionSource = Field(..., description="Data source information")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    confidence_level: ConfidenceLevel = Field(..., description="Confidence level category")

    # Multi-tenant
    tenant_id: str = Field(..., description="Tenant identifier")
    empresa_codigo: str = Field(..., description="Company code (WebPosto)")

    # Execution
    suggested_action: str = Field(..., description="Specific action to execute")
    action_button_text: str = Field(default="Executar Agora", description="Button text for UI")
    action_url: Optional[str] = Field(default=None, description="Deep link to execute action")

    # Metadata
    category: str = Field(
        ..., description="Category: revenue, expense, cash, inventory, staff, etc."
    )
    tags: List[str] = Field(default_factory=list, description="Tags for filtering")

    @property
    def is_expired(self) -> bool:
        """Check if action has expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    @property
    def is_high_confidence(self) -> bool:
        """Check if confidence is high enough to display (>= 80%)."""
        return self.confidence >= 0.8


class MoneyAtRiskFinding(BaseModel):
    """A finding about money at risk (potential loss)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"id": "risk_001", "title": "Revenue dropping 25%", "risk_type": "revenue_decline"}
            ]
        }
    )

    id: str = Field(..., description="Unique finding identifier")
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed explanation")

    # Risk specifics
    risk_type: str = Field(
        ..., description="Type: revenue_decline, expense_increase, cash_shortage, margin_drop, etc."
    )
    risk_subtype: Optional[str] = Field(default=None, description="Specific subtype")

    # Financial impact
    amount_at_risk: float = Field(..., description="Amount at risk in BRL")
    probability: float = Field(..., ge=0, le=1, description="Probability of loss occurring")
    timeframe_days: int = Field(..., description="Days until risk materializes")

    # Detection
    baseline_value: float = Field(..., description="Expected/normal value")
    current_value: float = Field(..., description="Current value")
    deviation_percent: float = Field(..., description="Percentage deviation from baseline")

    # Action
    action: DecisionAction = Field(..., description="Recommended action")

    # Trust
    confidence: float = Field(..., ge=0, le=1)
    source: DecisionSource = Field(...)


class RecoverableMoneyFinding(BaseModel):
    """A finding about recoverable money (missed revenue or overpayment)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "rec_001",
                    "title": "R$ 8,200 in overdue accounts",
                    "recovery_type": "overdue_receivable",
                }
            ]
        }
    )

    id: str = Field(..., description="Unique finding identifier")
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed explanation")

    # Recovery specifics
    recovery_type: str = Field(
        ...,
        description="Type: overdue_receivable, unbilled_sale, duplicate_payment, billing_error, etc.",
    )

    # Financial
    recoverable_amount: float = Field(..., description="Amount that can be recovered")
    recovery_probability: float = Field(
        ..., ge=0, le=1, description="Probability of successful recovery"
    )
    recovery_timeframe_days: int = Field(..., description="Expected days to recover")

    # Details
    affected_customers: Optional[int] = Field(
        default=None, description="Number of customers affected"
    )
    affected_transactions: Optional[int] = Field(default=None, description="Number of transactions")
    oldest_overdue_days: Optional[int] = Field(
        default=None, description="Days since oldest item became due"
    )

    # Action
    action: DecisionAction = Field(..., description="Recommended action")

    # Trust
    confidence: float = Field(..., ge=0, le=1)
    source: DecisionSource = Field(...)


class GrowthOpportunity(BaseModel):
    """A growth or optimization opportunity."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "opp_001",
                    "title": "Diesel sales up 40%",
                    "opportunity_type": "product_trend",
                }
            ]
        }
    )

    id: str = Field(..., description="Unique opportunity identifier")
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed explanation")

    # Opportunity specifics
    opportunity_type: str = Field(
        ...,
        description="Type: product_trend, margin_improvement, volume_increase, mix_optimization, etc.",
    )

    # Financial
    potential_revenue: float = Field(..., description="Potential additional revenue")
    potential_profit: float = Field(..., description="Potential additional profit")
    investment_required: Optional[float] = Field(
        default=None, description="Investment needed to capture"
    )
    roi_percent: Optional[float] = Field(default=None, description="Expected ROI percentage")

    # Details
    affected_products: Optional[List[str]] = Field(default=None, description="Products involved")
    trend_direction: str = Field(..., description="up, down, or stable")
    trend_strength: float = Field(..., ge=0, le=1, description="Strength of trend (0-1)")

    # Action
    action: DecisionAction = Field(..., description="Recommended action")

    # Trust
    confidence: float = Field(..., ge=0, le=1)
    source: DecisionSource = Field(...)


class DailyDecision(BaseModel):
    """A prioritized daily decision for the owner."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "dec_001",
                    "rank": 1,
                    "title": "Contact 3 overdue customers",
                    "total_score": 95.5,
                }
            ]
        }
    )

    id: str = Field(..., description="Unique decision identifier")
    rank: int = Field(..., ge=1, le=10, description="Priority rank (1 = highest)")

    # Content
    title: str = Field(..., description="Decision title")
    description: str = Field(..., description="Full description")
    decision_question: str = Field(..., description="Question the owner should answer")

    # Why this decision
    why_appeared: str = Field(..., description="Why did this decision appear?")
    why_ranked: str = Field(..., description="Why is it ranked at this position?")
    money_involved: str = Field(..., description="How much money is at stake?")
    what_rule_triggered: str = Field(..., description="Which rule triggered this decision?")

    # Scoring
    total_score: float = Field(..., ge=0, le=100, description="Priority score (0-100)")
    financial_impact_score: float = Field(..., ge=0, le=100)
    urgency_score: float = Field(..., ge=0, le=100)
    confidence_score: float = Field(..., ge=0, le=100)
    ease_score: float = Field(..., ge=0, le=100)
    time_score: float = Field(..., ge=0, le=100)

    # Action to take
    action: DecisionAction = Field(..., description="Recommended action")

    # Metadata
    decision_type: str = Field(..., description="risk, recovery, or opportunity")
    related_findings: List[str] = Field(default_factory=list, description="IDs of related findings")


class BusinessHealthMetrics(BaseModel):
    """Overall business health metrics."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"score": 78.5, "status": "attention", "trend": "improving"}]
        }
    )

    score: float = Field(..., ge=0, le=100, description="Overall health score (0-100)")
    status: str = Field(..., description="excellent, good, attention, critical")
    trend: str = Field(..., description="improving, stable, declining")
    trend_percent: float = Field(..., description="Percentage change trend")

    # Component scores
    revenue_health: float = Field(..., ge=0, le=100)
    expense_health: float = Field(..., ge=0, le=100)
    cash_health: float = Field(..., ge=0, le=100)
    margin_health: float = Field(..., ge=0, le=100)
    operational_health: float = Field(..., ge=0, le=100)

    # Summary
    summary: str = Field(..., description="Human-readable summary")
    recommendations: List[str] = Field(default_factory=list, description="Top recommendations")


class OwnerActionCenterSummary(BaseModel):
    """Complete summary for the Owner Action Center."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "tenant_id": "tenant_001",
                    "empresa_codigo": "11495",
                    "generated_at": "2026-06-29T10:00:00Z",
                }
            ]
        }
    )

    # Identification
    tenant_id: str = Field(..., description="Tenant identifier")
    empresa_codigo: str = Field(..., description="Company code")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    data_period_start: datetime = Field(..., description="Start of analysis period")
    data_period_end: datetime = Field(..., description="End of analysis period")

    # Business Health
    business_health: BusinessHealthMetrics = Field(..., description="Overall health metrics")

    # Money sections
    money_at_risk: List[MoneyAtRiskFinding] = Field(
        default_factory=list, description="Active risks"
    )
    money_at_risk_total: float = Field(..., description="Total money at risk")

    recoverable_money: List[RecoverableMoneyFinding] = Field(
        default_factory=list, description="Recoverable funds"
    )
    recoverable_total: float = Field(..., description="Total recoverable amount")

    opportunities: List[GrowthOpportunity] = Field(
        default_factory=list, description="Growth opportunities"
    )
    opportunity_total: float = Field(..., description="Total opportunity value")

    # Top decisions
    top_5_decisions: List[DailyDecision] = Field(..., description="Top 5 daily decisions")
    all_decisions: List[DailyDecision] = Field(default_factory=list, description="All decisions")

    # Executive summary
    executive_summary: str = Field(..., description="Brief executive summary")
    greeting: str = Field(..., description="Personalized greeting")

    # Quick stats
    total_actions: int = Field(...)
    critical_actions: int = Field(...)
    high_actions: int = Field(...)
    actions_requiring_immediate_attention: int = Field(...)

    # Trust
    confidence_average: float = Field(
        ..., ge=0, le=1, description="Average confidence across all findings"
    )
    data_sources: List[str] = Field(default_factory=list, description="Data sources used")

    # Preference model audit (FASE 5 — APRENDER)
    preference_audit: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Audit trail of preference weights applied to top 5 decisions",
    )


class BaselineConfig(BaseModel):
    """Configuration for baseline calculations."""

    lookback_days: int = Field(default=30, description="Days to look back for baseline")
    min_data_points: int = Field(default=7, description="Minimum data points required")
    outlier_threshold: float = Field(default=2.0, description="Z-score threshold for outliers")
    seasonal_adjustment: bool = Field(default=True, description="Adjust for day of week")


class RiskThresholds(BaseModel):
    """Thresholds for risk detection."""

    revenue_drop_percent: float = Field(default=20.0, description="Revenue drop threshold")
    expense_increase_percent: float = Field(default=30.0, description="Expense increase threshold")
    cash_shortage_threshold: float = Field(default=1000.0, description="Cash shortage threshold")
    margin_drop_percent: float = Field(default=5.0, description="Margin drop threshold")
    overdue_days: int = Field(default=7, description="Days until considered overdue")
