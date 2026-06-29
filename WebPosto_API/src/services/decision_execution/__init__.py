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
)

from .status_machine import DecisionStatusMachine, StatusTransitionError

from .execution_service import ExecutionService, ExecutionError

from .metrics_calculator import ExecutionMetricsCalculator

__all__ = [
    # Enums
    "DecisionStatus",
    "ConfirmationResult",
    "ImpactType",
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
    "ExecutionMetricsCalculator",
]
