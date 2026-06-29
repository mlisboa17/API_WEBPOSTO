"""
Decision Execution Models | LOGOS
==================================

Pydantic models for decision execution lifecycle.

Strict separation between:
- Estimated Impact (projections)
- Confirmed Impact (verified results)

All financial values tracked with evidence requirements.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import uuid4

from pydantic import BaseModel, Field, validator


class DecisionStatus(str, Enum):
    """
    Official decision lifecycle states.
    
    Flow:
        NEW → READY → EXECUTING → [COMPLETED | NOT_COMPLETED | PARTIAL] → ARCHIVED
    """
    NEW = "new"                           # Decision generated, not yet presented
    READY = "ready"                       # Presented to owner, awaiting execution
    EXECUTING = "executing"               # Owner clicked "Execute Now"
    COMPLETED = "completed"               # Action fully completed
    NOT_COMPLETED = "not_completed"       # Action not completed (with reason)
    PARTIAL = "partial"                   # Action partially completed
    ARCHIVED = "archived"                 # Decision archived after completion
    CANCELLED = "cancelled"               # Decision cancelled before execution
    EXPIRED = "expired"                   # Decision expired (> 7 days without action)


class ConfirmationResult(str, Enum):
    """Official confirmation outcomes."""
    YES = "yes"                           # Decision fully resolved the problem
    PARTIAL = "partial"                   # Decision partially resolved the problem
    NO = "no"                             # Decision did not resolve the problem


class ImpactType(str, Enum):
    """Types of financial impact."""
    RECOVERED = "recovered"               # Money recovered (collections, corrections)
    SAVED = "saved"                       # Money saved (negotiations, prevented losses)
    ADDITIONAL = "additional"             # Additional revenue (opportunities)
    PREVENTED = "prevented"               # Prevented losses (risk mitigation)


class RejectionReason(str, Enum):
    """Reasons for not completing a decision."""
    NOT_PRIORITY = "not_priority"         # Not a priority at the moment
    NO_TIME = "no_time"                   # Did not have time to execute
    INCORRECT_INFO = "incorrect_info"     # Information was incorrect
    ALREADY_RESOLVED = "already_resolved" # Problem resolved another way
    COULD_NOT_CONTACT = "could_not_contact"  # Could not contact relevant party
    EXTERNAL_BLOCKER = "external_blocker"  # External blocker prevented execution
    OTHER = "other"                       # Other reason


class PartialReason(str, Enum):
    """Reasons for partial completion."""
    AWAITING_RESPONSE = "awaiting_response"  # Waiting for external response
    IN_PROGRESS = "in_progress"             # Action in progress
    PARTIALLY_SUCCESSFUL = "partially_successful"  # Some success, not full
    REQUIRES_FOLLOWUP = "requires_followup"   # Requires additional follow-up


class DecisionAction(str, Enum):
    """Official decision action types for 'Execute Now' buttons."""
    EXECUTE_NOW = "execute_now"           # Generic execution
    VIEW_CUSTOMER = "view_customer"       # View customer details
    CHARGE = "charge"                     # Charge/collect from customer
    NEGOTIATE = "negotiate"               # Negotiate with supplier
    INVESTIGATE = "investigate"           # Investigate further
    OPEN_EXPENSE = "open_expense"         # Open expense record
    VIEW_CARDS = "view_cards"             # View card reconciliation
    VIEW_STOCK = "view_stock"             # View stock levels
    GO_TO_FINANCE = "go_to_finance"       # Navigate to financial module
    CALL = "call"                         # Make phone call
    EMAIL = "email"                       # Send email
    GENERATE_BOLETO = "generate_boleto"   # Generate payment slip


class TimelineEvent(BaseModel):
    """Single event in decision timeline."""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: DecisionStatus
    actor: str  # 'system' | 'user' | 'auto'
    action: str  # Description of what happened
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExecutionTimeline(BaseModel):
    """Complete timeline of decision lifecycle."""
    timeline_id: str = Field(default_factory=lambda: str(uuid4()))
    decision_id: str
    tenant_id: str
    empresa_codigo: str
    events: List[TimelineEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def add_event(
        self,
        status: DecisionStatus,
        actor: str,
        action: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TimelineEvent:
        """Add new event to timeline."""
        event = TimelineEvent(
            status=status,
            actor=actor,
            action=action,
            metadata=metadata
        )
        self.events.append(event)
        self.updated_at = datetime.utcnow()
        return event
    
    def get_duration_to_status(self, target_status: DecisionStatus) -> Optional[timedelta]:
        """Calculate time from creation to reaching target status."""
        start = self.created_at
        for event in self.events:
            if event.status == target_status:
                return event.timestamp - start
        return None
    
    def get_execution_duration(self) -> Optional[timedelta]:
        """Calculate time from EXECUTING to terminal state."""
        executing_time = None
        for event in self.events:
            if event.status == DecisionStatus.EXECUTING:
                executing_time = event.timestamp
            elif executing_time and event.status in [
                DecisionStatus.COMPLETED,
                DecisionStatus.NOT_COMPLETED,
                DecisionStatus.PARTIAL
            ]:
                return event.timestamp - executing_time
        return None


class EstimatedImpact(BaseModel):
    """
    Estimated financial impact BEFORE execution.
    
    These are projections, not facts.
    Must be clearly labeled as estimates in UI.
    """
    impact_id: str = Field(default_factory=lambda: str(uuid4()))
    impact_type: ImpactType
    currency: str = "BRL"
    amount: Decimal = Field(..., ge=0)
    
    # Estimation metadata
    confidence: float = Field(..., ge=0, le=1)  # Confidence in estimate (0-1)
    calculation_method: str  # How estimate was calculated
    baseline_value: Optional[Decimal] = None  # Historical baseline for comparison
    assumptions: List[str] = Field(default_factory=list)  # Assumptions made
    
    # Source
    source_engine: str  # Which engine generated estimate
    source_endpoint: Optional[str] = None
    
    # Display labels
    display_label: str = Field(
        default="",
        description="Label shown in UI, e.g., 'Estimado', 'Projetado'"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class ConfirmedImpact(BaseModel):
    """
    Confirmed financial impact AFTER execution.
    
    These are verified facts, not projections.
    Must have evidence or owner confirmation.
    """
    impact_id: str = Field(default_factory=lambda: str(uuid4()))
    confirmation_id: str  # Links to ResultConfirmation
    impact_type: ImpactType
    currency: str = "BRL"
    amount: Decimal = Field(..., ge=0)
    
    # Confirmation metadata
    verification_method: str  # 'owner_confirmed' | 'bank_statement' | 'invoice_comparison' | 'system_record'
    evidence_ids: List[str] = Field(default_factory=list)  # IDs of supporting evidence
    verified_by: Optional[str] = None  # User who verified (if manual)
    verified_at: Optional[datetime] = None
    
    # Variance from estimate
    estimated_amount: Optional[Decimal] = None  # Original estimate for comparison
    variance_percent: Optional[float] = None  # ((confirmed - estimated) / estimated) * 100
    variance_explanation: Optional[str] = None  # Why variance occurred
    
    # Display labels
    display_label: str = Field(
        default="Confirmado",
        description="Label shown in UI, e.g., 'Confirmado', 'Verificado'"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('variance_percent', always=True)
    def calculate_variance(cls, v, values):
        """Auto-calculate variance if estimated_amount provided."""
        if v is None and 'amount' in values and 'estimated_amount' in values:
            estimated = values.get('estimated_amount')
            actual = values.get('amount')
            if estimated and estimated > 0:
                return float((actual - estimated) / estimated) * 100
        return v
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class ResultConfirmation(BaseModel):
    """
    Owner confirmation of decision execution result.
    
    Separates estimated from confirmed impact.
    """
    confirmation_id: str = Field(default_factory=lambda: str(uuid4()))
    decision_id: str
    tenant_id: str
    empresa_codigo: str
    
    # Confirmation result
    result: ConfirmationResult
    confirmed_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_by: str  # User ID
    
    # Impact (only if YES or PARTIAL)
    confirmed_impact: Optional[ConfirmedImpact] = None
    
    # Partial completion details
    partial_progress_percent: Optional[float] = Field(None, ge=0, le=100)
    partial_reason: Optional[PartialReason] = None
    partial_details: Optional[str] = None
    next_action: Optional[str] = None  # Recommended next step
    
    # Rejection details (only if NO)
    rejection_reason: Optional[RejectionReason] = None
    rejection_details: Optional[str] = None
    
    # Time tracking
    time_spent_minutes: Optional[int] = None  # How long execution took
    
    # Notes
    notes: Optional[str] = None
    
    # Metadata
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExecutionRecord(BaseModel):
    """
    Complete record of decision execution.
    
    Includes:
    - Decision metadata
    - Execution timeline
    - Estimated impact (before)
    - Confirmed impact (after)
    - Result confirmation
    """
    # Identification
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    decision_id: str
    tenant_id: str
    empresa_codigo: str
    
    # Decision metadata
    decision_title: str
    decision_category: str
    decision_type: str
    priority: str
    
    # Status
    current_status: DecisionStatus = DecisionStatus.NEW
    
    # Timeline
    timeline: ExecutionTimeline
    
    # Impact (strict separation)
    estimated_impact: EstimatedImpact  # Projection (always present)
    confirmed_impact: Optional[ConfirmedImpact] = None  # Fact (only after confirmation)
    
    # Result confirmation
    confirmation: Optional[ResultConfirmation] = None
    
    # Execution action
    action_type: DecisionAction
    action_context: Dict[str, Any] = Field(default_factory=dict)  # Pre-loaded context
    action_url: Optional[str] = None  # Deep link to relevant screen
    
    # Confidence
    confidence_score: float = Field(..., ge=0, le=100)
    
    # Source
    source_engine: str
    source_endpoint: Optional[str] = None
    
    # Metadata
    expires_at: Optional[datetime] = None  # Auto-expire if not executed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def is_expired(self) -> bool:
        """Check if decision has expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        # Default expiration: 7 days from READY
        if self.current_status == DecisionStatus.READY:
            ready_event = next(
                (e for e in self.timeline.events if e.status == DecisionStatus.READY),
                None
            )
            if ready_event:
                return datetime.utcnow() > ready_event.timestamp + timedelta(days=7)
        return False
    
    def get_time_to_execute(self) -> Optional[timedelta]:
        """Calculate time from READY to EXECUTING."""
        return self.timeline.get_duration_to_status(DecisionStatus.EXECUTING)
    
    def get_execution_duration(self) -> Optional[timedelta]:
        """Calculate time spent executing."""
        return self.timeline.get_execution_duration()
    
    def get_impact_variance(self) -> Optional[float]:
        """Calculate variance between estimated and confirmed impact."""
        if self.confirmed_impact and self.confirmed_impact.variance_percent is not None:
            return self.confirmed_impact.variance_percent
        return None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExecutionMetrics(BaseModel):
    """Metrics for decision execution effectiveness."""
    
    # Period
    period_start: datetime
    period_end: datetime
    tenant_id: Optional[str] = None  # None = all tenants
    
    # Volume
    decisions_generated: int = 0
    decisions_presented: int = 0
    decisions_executed: int = 0
    decisions_completed: int = 0
    decisions_not_completed: int = 0
    decisions_partial: int = 0
    decisions_expired: int = 0
    
    # Rates
    @property
    def presentation_rate(self) -> float:
        """Percentage of generated decisions that were presented."""
        if self.decisions_generated == 0:
            return 0.0
        return (self.decisions_presented / self.decisions_generated) * 100
    
    @property
    def execution_rate(self) -> float:
        """Percentage of presented decisions that were executed."""
        if self.decisions_presented == 0:
            return 0.0
        return (self.decisions_executed / self.decisions_presented) * 100
    
    @property
    def completion_rate(self) -> float:
        """Percentage of executed decisions fully completed."""
        if self.decisions_executed == 0:
            return 0.0
        return (self.decisions_completed / self.decisions_executed) * 100
    
    @property
    def success_rate(self) -> float:
        """Percentage of executed decisions with YES or PARTIAL result."""
        if self.decisions_executed == 0:
            return 0.0
        successful = self.decisions_completed + self.decisions_partial
        return (successful / self.decisions_executed) * 100
    
    # Timing
    avg_time_to_execute_minutes: Optional[float] = None  # From READY to EXECUTING
    avg_execution_duration_minutes: Optional[float] = None  # From EXECUTING to terminal
    
    # Financial (strict separation)
    total_estimated_impact: Decimal = Decimal("0")
    total_confirmed_impact: Decimal = Decimal("0")
    
    @property
    def confirmation_rate(self) -> float:
        """Percentage of estimated impact that was confirmed."""
        if self.total_estimated_impact == 0:
            return 0.0
        return float(self.total_confirmed_impact / self.total_estimated_impact) * 100
    
    # Impact by type (confirmed only)
    recovered_amount: Decimal = Decimal("0")
    saved_amount: Decimal = Decimal("0")
    additional_amount: Decimal = Decimal("0")
    prevented_amount: Decimal = Decimal("0")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class ExecutionSummary(BaseModel):
    """Summary of execution status for dashboard display."""
    
    tenant_id: str
    empresa_codigo: str
    
    # Pending
    pending_count: int = 0
    pending_estimated_value: Decimal = Decimal("0")
    urgent_count: int = 0  # Priority = CRITICAL or HIGH
    
    # Today's activity
    executed_today: int = 0
    completed_today: int = 0
    confirmed_today_value: Decimal = Decimal("0")
    
    # This period (default: month)
    period_generated: int = 0
    period_executed: int = 0
    period_completion_rate: float = 0.0
    period_confirmed_value: Decimal = Decimal("0")
    
    # All time
    total_executed: int = 0
    total_completed: int = 0
    total_confirmed_value: Decimal = Decimal("0")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
