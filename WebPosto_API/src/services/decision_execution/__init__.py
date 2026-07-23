"""
Decision Execution Platform | LOGOS
=====================================

Execution lifecycle management for owner decisions.

Status Flow:
    NEW → READY → EXECUTING → [COMPLETED | NOT_COMPLETED | PARTIAL] → ARCHIVED

Features:
- Decision Status Machine
- Execution Timeline
- Result Confirmation
- Real vs Estimated Impact Separation
- Execution Metrics

Usage:
    from src.services.decision_execution import (
        DecisionStatusMachine,
        ExecutionService,
        ExecutionRecord,
        ResultConfirmation,
        ExecutionMetricsCalculator,
    )
"""

from .models import (
    DecisionStatus,
    ExecutionRecord,
    ResultConfirmation,
    ConfirmationResult,
    ExecutionTimeline,
    TimelineEvent,
    EstimatedImpact,
    ConfirmedImpact,
    ImpactType,
    DecisionAction,
    PartialReason,
    RejectionReason,
)

from .status_machine import DecisionStatusMachine, StatusTransitionError

from .execution_service import ExecutionService, ExecutionError, ConfirmationError

from .execution_store import ExecutionRecordStore

from .sql_store import SQLExecutionRecordStore

from .metrics_calculator import ExecutionMetricsCalculator

from .feedback import ExecutionFeedbackService

from .behavior_analytics import BehaviorAnalyticsService

__all__ = [
    # Enums
    "DecisionStatus",
    "ConfirmationResult",
    "ImpactType",
    "DecisionAction",
    "PartialReason",
    "RejectionReason",
    # Models
    "ExecutionRecord",
    "ResultConfirmation",
    "ExecutionTimeline",
    "TimelineEvent",
    "EstimatedImpact",
    "ConfirmedImpact",
    # Services
    "DecisionStatusMachine",
    "StatusTransitionError",
    "ExecutionService",
    "ExecutionError",
    "ConfirmationError",
    "ExecutionRecordStore",
    "SQLExecutionRecordStore",
    "ExecutionMetricsCalculator",
    "ExecutionFeedbackService",
    "BehaviorAnalyticsService",
]
