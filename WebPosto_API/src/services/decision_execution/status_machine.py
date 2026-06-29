"""
Decision Status Machine | LOGOS
================================

State machine for decision lifecycle management.

Valid Transitions:
    NEW → READY → EXECUTING → COMPLETED → ARCHIVED
                        ↓
                  NOT_COMPLETED
                        ↓
                    PARTIAL

All transitions require timestamp logging.
All terminal states transition to ARCHIVED after 30 days.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from enum import Enum

from .models import (
    DecisionStatus,
    ExecutionRecord,
    ExecutionTimeline,
    TimelineEvent,
)


class StatusTransitionError(Exception):
    """Raised when invalid status transition attempted."""
    pass


class TransitionRule:
    """Rule for validating and executing status transitions."""
    
    def __init__(
        self,
        from_status: DecisionStatus,
        to_status: DecisionStatus,
        required_fields: Optional[List[str]] = None,
        validator: Optional[Callable[[ExecutionRecord], bool]] = None,
        auto_archive_after_days: Optional[int] = None
    ):
        self.from_status = from_status
        self.to_status = to_status
        self.required_fields = required_fields or []
        self.validator = validator
        self.auto_archive_after_days = auto_archive_after_days


class DecisionStatusMachine:
    """
    State machine for decision lifecycle.
    
    Ensures valid transitions, records timestamps,
    and manages automatic expiration/archival.
    """
    
    # Valid transitions with rules
    TRANSITIONS: Dict[tuple, TransitionRule] = {
        # NEW can transition to READY (presented) or CANCELLED
        (DecisionStatus.NEW, DecisionStatus.READY): TransitionRule(
            DecisionStatus.NEW, DecisionStatus.READY,
            required_fields=["decision_title", "estimated_impact"]
        ),
        (DecisionStatus.NEW, DecisionStatus.CANCELLED): TransitionRule(
            DecisionStatus.NEW, DecisionStatus.CANCELLED,
            required_fields=["cancellation_reason"]
        ),
        
        # READY can transition to EXECUTING, EXPIRED, or CANCELLED
        (DecisionStatus.READY, DecisionStatus.EXECUTING): TransitionRule(
            DecisionStatus.READY, DecisionStatus.EXECUTING,
            required_fields=["action_type"]
        ),
        (DecisionStatus.READY, DecisionStatus.EXPIRED): TransitionRule(
            DecisionStatus.READY, DecisionStatus.EXPIRED,
            validator=lambda record: record.is_expired()
        ),
        (DecisionStatus.READY, DecisionStatus.CANCELLED): TransitionRule(
            DecisionStatus.READY, DecisionStatus.CANCELLED
        ),
        
        # EXECUTING can transition to terminal states
        (DecisionStatus.EXECUTING, DecisionStatus.COMPLETED): TransitionRule(
            DecisionStatus.EXECUTING, DecisionStatus.COMPLETED,
            required_fields=["confirmation"]
        ),
        (DecisionStatus.EXECUTING, DecisionStatus.NOT_COMPLETED): TransitionRule(
            DecisionStatus.EXECUTING, DecisionStatus.NOT_COMPLETED,
            required_fields=["confirmation"]
        ),
        (DecisionStatus.EXECUTING, DecisionStatus.PARTIAL): TransitionRule(
            DecisionStatus.EXECUTING, DecisionStatus.PARTIAL,
            required_fields=["confirmation"]
        ),
        
        # Terminal states can transition to ARCHIVED
        (DecisionStatus.COMPLETED, DecisionStatus.ARCHIVED): TransitionRule(
            DecisionStatus.COMPLETED, DecisionStatus.ARCHIVED,
            auto_archive_after_days=30
        ),
        (DecisionStatus.NOT_COMPLETED, DecisionStatus.ARCHIVED): TransitionRule(
            DecisionStatus.NOT_COMPLETED, DecisionStatus.ARCHIVED,
            auto_archive_after_days=30
        ),
        (DecisionStatus.PARTIAL, DecisionStatus.ARCHIVED): TransitionRule(
            DecisionStatus.PARTIAL, DecisionStatus.ARCHIVED,
            auto_archive_after_days=30
        ),
        (DecisionStatus.EXPIRED, DecisionStatus.ARCHIVED): TransitionRule(
            DecisionStatus.EXPIRED, DecisionStatus.ARCHIVED,
            auto_archive_after_days=7
        ),
        (DecisionStatus.CANCELLED, DecisionStatus.ARCHIVED): TransitionRule(
            DecisionStatus.CANCELLED, DecisionStatus.ARCHIVED,
            auto_archive_after_days=7
        ),
    }
    
    @classmethod
    def can_transition(
        cls,
        record: ExecutionRecord,
        to_status: DecisionStatus
    ) -> tuple[bool, Optional[str]]:
        """
        Check if transition is valid.
        
        Returns:
            (is_valid, error_message)
        """
        from_status = record.current_status
        
        # Check if transition exists
        key = (from_status, to_status)
        if key not in cls.TRANSITIONS:
            return False, f"Invalid transition: {from_status.value} → {to_status.value}"
        
        rule = cls.TRANSITIONS[key]
        
        # Check required fields
        for field in rule.required_fields:
            value = getattr(record, field, None)
            if value is None:
                return False, f"Required field '{field}' missing for transition"
        
        # Run custom validator
        if rule.validator and not rule.validator(record):
            return False, f"Validation failed for transition to {to_status.value}"
        
        return True, None
    
    @classmethod
    def transition(
        cls,
        record: ExecutionRecord,
        to_status: DecisionStatus,
        actor: str = "system",
        action: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExecutionRecord:
        """
        Execute status transition.
        
        Args:
            record: Execution record to update
            to_status: Target status
            actor: Who/what triggered transition ('system' | 'user' | 'auto')
            action: Description of the action
            metadata: Additional context
            
        Returns:
            Updated ExecutionRecord
            
        Raises:
            StatusTransitionError: If transition is invalid
        """
        # Validate transition
        is_valid, error = cls.can_transition(record, to_status)
        if not is_valid:
            raise StatusTransitionError(error)
        
        # Default action description
        if action is None:
            action = f"Status changed from {record.current_status.value} to {to_status.value}"
        
        # Update record status
        record.current_status = to_status
        record.updated_at = datetime.utcnow()
        
        # Add timeline event
        record.timeline.add_event(
            status=to_status,
            actor=actor,
            action=action,
            metadata={
                "previous_status": record.current_status.value,
                **(metadata or {})
            }
        )
        
        return record
    
    @classmethod
    def present(cls, record: ExecutionRecord) -> ExecutionRecord:
        """Transition from NEW to READY (decision shown to owner)."""
        return cls.transition(
            record,
            DecisionStatus.READY,
            actor="system",
            action="Decision presented to owner"
        )
    
    @classmethod
    def start_execution(cls, record: ExecutionRecord, user_id: str) -> ExecutionRecord:
        """Transition from READY to EXECUTING (owner clicked Execute Now)."""
        return cls.transition(
            record,
            DecisionStatus.EXECUTING,
            actor="user",
            action="Owner started execution",
            metadata={"user_id": user_id}
        )
    
    @classmethod
    def complete(
        cls,
        record: ExecutionRecord,
        confirmation_id: str,
        user_id: str
    ) -> ExecutionRecord:
        """Transition from EXECUTING to COMPLETED."""
        return cls.transition(
            record,
            DecisionStatus.COMPLETED,
            actor="user",
            action="Execution completed successfully",
            metadata={
                "confirmation_id": confirmation_id,
                "user_id": user_id
            }
        )
    
    @classmethod
    def mark_not_completed(
        cls,
        record: ExecutionRecord,
        confirmation_id: str,
        user_id: str,
        reason: str
    ) -> ExecutionRecord:
        """Transition from EXECUTING to NOT_COMPLETED."""
        return cls.transition(
            record,
            DecisionStatus.NOT_COMPLETED,
            actor="user",
            action=f"Execution not completed: {reason}",
            metadata={
                "confirmation_id": confirmation_id,
                "user_id": user_id,
                "reason": reason
            }
        )
    
    @classmethod
    def mark_partial(
        cls,
        record: ExecutionRecord,
        confirmation_id: str,
        user_id: str,
        progress_percent: float
    ) -> ExecutionRecord:
        """Transition from EXECUTING to PARTIAL."""
        return cls.transition(
            record,
            DecisionStatus.PARTIAL,
            actor="user",
            action=f"Execution partially completed ({progress_percent}%)",
            metadata={
                "confirmation_id": confirmation_id,
                "user_id": user_id,
                "progress_percent": progress_percent
            }
        )
    
    @classmethod
    def expire(cls, record: ExecutionRecord) -> ExecutionRecord:
        """Transition to EXPIRED (auto or manual)."""
        return cls.transition(
            record,
            DecisionStatus.EXPIRED,
            actor="auto",
            action="Decision expired - no action taken within 7 days"
        )
    
    @classmethod
    def cancel(cls, record: ExecutionRecord, reason: str, user_id: Optional[str] = None) -> ExecutionRecord:
        """Transition to CANCELLED."""
        actor = "user" if user_id else "system"
        return cls.transition(
            record,
            DecisionStatus.CANCELLED,
            actor=actor,
            action=f"Decision cancelled: {reason}",
            metadata={
                "reason": reason,
                "cancelled_by": user_id
            }
        )
    
    @classmethod
    def archive(cls, record: ExecutionRecord) -> ExecutionRecord:
        """Transition terminal state to ARCHIVED."""
        return cls.transition(
            record,
            DecisionStatus.ARCHIVED,
            actor="auto",
            action="Decision archived"
        )
    
    @classmethod
    def check_expiration(cls, record: ExecutionRecord) -> Optional[ExecutionRecord]:
        """
        Check and auto-expire if decision has been READY for > 7 days.
        
        Returns:
            Updated record if expired, None otherwise
        """
        if record.current_status != DecisionStatus.READY:
            return None
        
        if record.is_expired():
            return cls.expire(record)
        
        return None
    
    @classmethod
    def check_archival(cls, record: ExecutionRecord) -> Optional[ExecutionRecord]:
        """
        Check and auto-archive if terminal state is old enough.
        
        Returns:
            Updated record if archived, None otherwise
        """
        # Only archive terminal states
        if record.current_status not in [
            DecisionStatus.COMPLETED,
            DecisionStatus.NOT_COMPLETED,
            DecisionStatus.PARTIAL,
            DecisionStatus.EXPIRED,
            DecisionStatus.CANCELLED
        ]:
            return None
        
        # Find when we entered terminal state
        terminal_event = None
        for event in reversed(record.timeline.events):
            if event.status == record.current_status:
                terminal_event = event
                break
        
        if not terminal_event:
            return None
        
        # Get archival rule
        key = (record.current_status, DecisionStatus.ARCHIVED)
        rule = cls.TRANSITIONS.get(key)
        if not rule or not rule.auto_archive_after_days:
            return None
        
        # Check if enough time has passed
        archive_after = terminal_event.timestamp + timedelta(days=rule.auto_archive_after_days)
        if datetime.utcnow() >= archive_after:
            return cls.archive(record)
        
        return None
    
    @classmethod
    def get_valid_transitions(cls, current_status: DecisionStatus) -> List[DecisionStatus]:
        """Get list of valid next states from current status."""
        valid = []
        for (from_status, to_status), rule in cls.TRANSITIONS.items():
            if from_status == current_status:
                valid.append(to_status)
        return valid
