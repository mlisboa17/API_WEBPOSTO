"""Estados do DATA-ON-DEMAND. Sem I/O."""

from __future__ import annotations

from enum import StrEnum


class DataRequestState(StrEnum):
    ALREADY_AVAILABLE = "ALREADY_AVAILABLE"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    VALIDATING = "VALIDATING"
    COMMITTING = "COMMITTING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    LOCKED = "LOCKED"


ACTIVE_STATES = frozenset(
    {
        DataRequestState.AWAITING_CONFIRMATION,
        DataRequestState.QUEUED,
        DataRequestState.RUNNING,
        DataRequestState.VALIDATING,
        DataRequestState.COMMITTING,
        DataRequestState.LOCKED,
    }
)

TERMINAL_STATES = frozenset(
    {
        DataRequestState.SUCCESS,
        DataRequestState.PARTIAL,
        DataRequestState.FAILED,
        DataRequestState.CANCELLED,
        DataRequestState.EXPIRED,
    }
)

CANCELABLE_STATES = frozenset(
    {
        DataRequestState.AWAITING_CONFIRMATION,
        DataRequestState.QUEUED,
    }
)

NON_CANCELABLE_EXECUTION = frozenset(
    {
        DataRequestState.RUNNING,
        DataRequestState.VALIDATING,
        DataRequestState.COMMITTING,
    }
)
