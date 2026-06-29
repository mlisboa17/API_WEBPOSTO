"""
Execution Service | LOGOS
==========================

Main service for decision execution lifecycle.

Handles:
- Decision presentation to owner
- Execution start
- Result confirmation
- Impact verification
- Timeline management

Strict separation between estimated and confirmed impact.
All financial claims require evidence.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import uuid4

from .models import (
    DecisionStatus,
    DecisionAction,
    ExecutionRecord,
    ExecutionTimeline,
    ResultConfirmation,
    ConfirmationResult,
    RejectionReason,
    PartialReason,
    EstimatedImpact,
    ConfirmedImpact,
    ImpactType,
)
from .status_machine import DecisionStatusMachine, StatusTransitionError


class ExecutionError(Exception):
    """Raised when execution operation fails."""
    pass


class ConfirmationError(Exception):
    """Raised when confirmation is invalid."""
    pass


class ExecutionService:
    """
    Service for managing decision execution.
    
    Ensures:
    - Valid state transitions
    - Strict impact separation (estimated vs confirmed)
    - Complete audit trail
    - Evidence-based financial claims
    """
    
    def __init__(self, repository=None):
        """
        Initialize execution service.
        
        Args:
            repository: Data repository for persistence (optional)
        """
        self.repository = repository
    
    def create_decision(
        self,
        decision_id: str,
        tenant_id: str,
        empresa_codigo: str,
        title: str,
        category: str,
        decision_type: str,
        priority: str,
        action_type: DecisionAction,
        estimated_impact: EstimatedImpact,
        confidence_score: float,
        source_engine: str,
        source_endpoint: Optional[str] = None,
        action_context: Optional[Dict[str, Any]] = None,
        action_url: Optional[str] = None,
        expires_in_days: int = 7
    ) -> ExecutionRecord:
        """
        Create new execution record for a decision.
        
        Args:
            decision_id: Unique decision identifier
            tenant_id: Tenant identifier
            empresa_codigo: Company code
            title: Decision title
            category: Decision category
            decision_type: Decision type
            priority: Priority level
            action_type: Type of action to execute
            estimated_impact: Projected financial impact (ESTIMATE, NOT FACT)
            confidence_score: Confidence in decision (0-100)
            source_engine: Engine that generated decision
            source_endpoint: API endpoint source
            action_context: Pre-loaded context for execution
            action_url: Deep link to relevant screen
            expires_in_days: Days until auto-expiration
            
        Returns:
            New ExecutionRecord in NEW status
        """
        # Create timeline
        timeline = ExecutionTimeline(
            decision_id=decision_id,
            tenant_id=tenant_id,
            empresa_codigo=empresa_codigo
        )
        
        # Add creation event
        timeline.add_event(
            status=DecisionStatus.NEW,
            actor="system",
            action="Decision created and queued for presentation",
            metadata={
                "source_engine": source_engine,
                "estimated_impact": {
                    "type": estimated_impact.impact_type.value,
                    "amount": float(estimated_impact.amount),
                    "confidence": estimated_impact.confidence,
                    "label": "ESTIMADO"  # Always label as estimate
                }
            }
        )
        
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create record
        record = ExecutionRecord(
            decision_id=decision_id,
            tenant_id=tenant_id,
            empresa_codigo=empresa_codigo,
            decision_title=title,
            decision_category=category,
            decision_type=decision_type,
            priority=priority,
            current_status=DecisionStatus.NEW,
            timeline=timeline,
            estimated_impact=estimated_impact,
            action_type=action_type,
            action_context=action_context or {},
            action_url=action_url,
            confidence_score=confidence_score,
            source_engine=source_engine,
            source_endpoint=source_endpoint,
            expires_at=expires_at
        )
        
        # Persist if repository available
        if self.repository:
            self.repository.save(record)
        
        return record
    
    def present_decision(self, record: ExecutionRecord) -> ExecutionRecord:
        """
        Present decision to owner (transition NEW → READY).
        
        Args:
            record: Execution record
            
        Returns:
            Updated record in READY status
        """
        # Use status machine for transition
        record = DecisionStatusMachine.present(record)
        
        # Persist
        if self.repository:
            self.repository.save(record)
        
        return record
    
    def execute_decision(
        self,
        record: ExecutionRecord,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Start decision execution (transition READY → EXECUTING).
        
        Returns context and URL for execution.
        
        Args:
            record: Execution record
            user_id: User starting execution
            
        Returns:
            Execution context including:
            - action_type: Type of action
            - action_context: Pre-loaded data
            - action_url: Deep link
            - execution_record: Updated record
            
        Raises:
            ExecutionError: If execution cannot start
        """
        # Validate status
        if record.current_status != DecisionStatus.READY:
            raise ExecutionError(
                f"Cannot execute decision in {record.current_status.value} status. "
                "Decision must be in READY status."
            )
        
        # Check expiration
        if record.is_expired():
            DecisionStatusMachine.expire(record)
            raise ExecutionError(
                "Decision has expired. Cannot execute expired decisions."
            )
        
        # Transition to EXECUTING
        record = DecisionStatusMachine.start_execution(record, user_id)
        
        # Persist
        if self.repository:
            self.repository.save(record)
        
        # Return execution context
        return {
            "execution_id": record.execution_id,
            "decision_id": record.decision_id,
            "action_type": record.action_type.value,
            "action_context": record.action_context,
            "action_url": record.action_url,
            "estimated_impact": {
                "type": record.estimated_impact.impact_type.value,
                "amount": float(record.estimated_impact.amount),
                "currency": record.estimated_impact.currency,
                "label": "ESTIMADO",  # Always mark as estimate
                "confidence": record.estimated_impact.confidence
            },
            "execution_record": record
        }
    
    def confirm_result(
        self,
        record: ExecutionRecord,
        user_id: str,
        result: ConfirmationResult,
        confirmed_amount: Optional[Decimal] = None,
        verification_method: str = "owner_confirmed",
        evidence_ids: Optional[List[str]] = None,
        time_spent_minutes: Optional[int] = None,
        notes: Optional[str] = None,
        # Partial completion details
        partial_progress: Optional[float] = None,
        partial_reason: Optional[PartialReason] = None,
        partial_details: Optional[str] = None,
        next_action: Optional[str] = None,
        # Rejection details
        rejection_reason: Optional[RejectionReason] = None,
        rejection_details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ExecutionRecord:
        """
        Confirm execution result with strict impact separation.
        
        This is the CRITICAL method that separates estimates from facts.
        
        Args:
            record: Execution record (must be in EXECUTING status)
            user_id: User confirming result
            result: YES | PARTIAL | NO
            confirmed_amount: Verified financial impact (only for YES/PARTIAL)
            verification_method: How impact was verified
            evidence_ids: IDs of supporting evidence
            time_spent_minutes: Time spent on execution
            notes: Additional notes
            partial_progress: % completed (only for PARTIAL)
            partial_reason: Why partial (only for PARTIAL)
            partial_details: Details (only for PARTIAL)
            next_action: Recommended next step (only for PARTIAL)
            rejection_reason: Why not completed (only for NO)
            rejection_details: Details (only for NO)
            ip_address: User's IP
            user_agent: User's browser
            
        Returns:
            Updated record with confirmation
            
        Raises:
            ConfirmationError: If confirmation is invalid
            ExecutionError: If record not in EXECUTING status
        """
        # Validate status
        if record.current_status != DecisionStatus.EXECUTING:
            raise ExecutionError(
                f"Cannot confirm decision in {record.current_status.value} status. "
                "Decision must be in EXECUTING status."
            )
        
        # Validate result-specific fields
        if result == ConfirmationResult.YES:
            if confirmed_amount is None:
                raise ConfirmationError(
                    "YES result requires confirmed_amount. "
                    "Cannot claim impact without verification."
                )
        elif result == ConfirmationResult.PARTIAL:
            if partial_progress is None or partial_reason is None:
                raise ConfirmationError(
                    "PARTIAL result requires partial_progress and partial_reason."
                )
        elif result == ConfirmationResult.NO:
            if rejection_reason is None:
                raise ConfirmationError(
                    "NO result requires rejection_reason. "
                    "Need to understand why decision wasn't executed."
                )
        
        # Create confirmation record
        confirmation_id = str(uuid4())
        confirmation = ResultConfirmation(
            confirmation_id=confirmation_id,
            decision_id=record.decision_id,
            tenant_id=record.tenant_id,
            empresa_codigo=record.empresa_codigo,
            result=result,
            confirmed_by=user_id,
            confirmed_at=datetime.utcnow(),
            time_spent_minutes=time_spent_minutes,
            notes=notes,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Add result-specific details
        if result == ConfirmationResult.YES:
            # SUCCESS: Create confirmed impact
            confirmed_impact = ConfirmedImpact(
                confirmation_id=confirmation_id,
                impact_type=record.estimated_impact.impact_type,
                currency=record.estimated_impact.currency,
                amount=confirmed_amount,
                verification_method=verification_method,
                evidence_ids=evidence_ids or [],
                verified_by=user_id,
                verified_at=datetime.utcnow(),
                estimated_amount=record.estimated_impact.amount,
                display_label="CONFIRMADO"  # Mark as confirmed fact
            )
            record.confirmed_impact = confirmed_impact
            confirmation.confirmed_impact = confirmed_impact
            
            # Transition to COMPLETED
            record = DecisionStatusMachine.complete(
                record, confirmation_id, user_id
            )
            
        elif result == ConfirmationResult.PARTIAL:
            # PARTIAL: Create confirmed impact for partial amount
            if confirmed_amount:
                confirmed_impact = ConfirmedImpact(
                    confirmation_id=confirmation_id,
                    impact_type=record.estimated_impact.impact_type,
                    currency=record.estimated_impact.currency,
                    amount=confirmed_amount,
                    verification_method=verification_method,
                    evidence_ids=evidence_ids or [],
                    verified_by=user_id,
                    verified_at=datetime.utcnow(),
                    estimated_amount=record.estimated_impact.amount * Decimal(str(partial_progress / 100)),
                    display_label="PARCIALMENTE CONFIRMADO"
                )
                record.confirmed_impact = confirmed_impact
                confirmation.confirmed_impact = confirmed_impact
            
            confirmation.partial_progress_percent = partial_progress
            confirmation.partial_reason = partial_reason
            confirmation.partial_details = partial_details
            confirmation.next_action = next_action
            
            # Transition to PARTIAL
            record = DecisionStatusMachine.mark_partial(
                record, confirmation_id, user_id, partial_progress
            )
            
        elif result == ConfirmationResult.NO:
            # NOT COMPLETED: Record rejection reason
            confirmation.rejection_reason = rejection_reason
            confirmation.rejection_details = rejection_details
            
            # No confirmed impact (obviously)
            record.confirmed_impact = None
            
            # Transition to NOT_COMPLETED
            record = DecisionStatusMachine.mark_not_completed(
                record, confirmation_id, user_id, rejection_reason.value
            )
        
        # Store confirmation
        record.confirmation = confirmation
        
        # Persist
        if self.repository:
            self.repository.save(record)
        
        return record
    
    def get_execution_context(self, record: ExecutionRecord) -> Dict[str, Any]:
        """
        Get full execution context for UI rendering.
        
        Returns both estimated and confirmed impact with clear labeling.
        """
        context = {
            "execution_id": record.execution_id,
            "decision_id": record.decision_id,
            "status": record.current_status.value,
            "title": record.decision_title,
            "category": record.decision_category,
            "priority": record.priority,
            "action_type": record.action_type.value,
            "action_context": record.action_context,
            "action_url": record.action_url,
            "confidence_score": record.confidence_score,
            "timeline": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "status": e.status.value,
                    "actor": e.actor,
                    "action": e.action
                }
                for e in record.timeline.events
            ]
        }
        
        # ALWAYS include estimated impact with ESTIMADO label
        context["estimated_impact"] = {
            "type": record.estimated_impact.impact_type.value,
            "amount": float(record.estimated_impact.amount),
            "currency": record.estimated_impact.currency,
            "label": "ESTIMADO",  # NEVER remove this label
            "confidence": record.estimated_impact.confidence,
            "calculation_method": record.estimated_impact.calculation_method
        }
        
        # Only include confirmed impact if available
        if record.confirmed_impact:
            context["confirmed_impact"] = {
                "type": record.confirmed_impact.impact_type.value,
                "amount": float(record.confirmed_impact.amount),
                "currency": record.confirmed_impact.currency,
                "label": record.confirmed_impact.display_label,  # CONFIRMADO or PARCIAL
                "verification_method": record.confirmed_impact.verification_method,
                "variance_percent": record.confirmed_impact.variance_percent
            }
        
        # Include confirmation if available
        if record.confirmation:
            context["confirmation"] = {
                "result": record.confirmation.result.value,
                "confirmed_at": record.confirmation.confirmed_at.isoformat(),
                "time_spent_minutes": record.confirmation.time_spent_minutes
            }
            
            if record.confirmation.result == ConfirmationResult.PARTIAL:
                context["confirmation"]["partial_progress"] = record.confirmation.partial_progress_percent
                context["confirmation"]["next_action"] = record.confirmation.next_action
            
            elif record.confirmation.result == ConfirmationResult.NO:
                context["confirmation"]["rejection_reason"] = record.confirmation.rejection_reason.value
        
        return context
    
    def cancel_decision(
        self,
        record: ExecutionRecord,
        reason: str,
        user_id: Optional[str] = None
    ) -> ExecutionRecord:
        """Cancel decision before execution."""
        record = DecisionStatusMachine.cancel(record, reason, user_id)
        
        if self.repository:
            self.repository.save(record)
        
        return record
    
    def check_expiration(self, record: ExecutionRecord) -> Optional[ExecutionRecord]:
        """Check and auto-expire if needed."""
        expired = DecisionStatusMachine.check_expiration(record)
        
        if expired and self.repository:
            self.repository.save(expired)
        
        return expired
    
    def check_archival(self, record: ExecutionRecord) -> Optional[ExecutionRecord]:
        """Check and auto-archive if needed."""
        archived = DecisionStatusMachine.check_archival(record)
        
        if archived and self.repository:
            self.repository.save(archived)
        
        return archived
