"""DIR-01D — contrato ExecutiveReviewRequest."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ReviewRequestType(str, Enum):
    NOMINAL_IDENTIFICATION_REVIEW = "NOMINAL_IDENTIFICATION_REVIEW"


class ReviewRequestStatus(str, Enum):
    REQUESTED = "REQUESTED"
    ASSIGNED = "ASSIGNED"
    IN_REVIEW = "IN_REVIEW"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


ACTIVE_STATUSES = frozenset(
    {
        ReviewRequestStatus.REQUESTED,
        ReviewRequestStatus.ASSIGNED,
        ReviewRequestStatus.IN_REVIEW,
        ReviewRequestStatus.NEEDS_INFORMATION,
    }
)


class CreateReviewRequestBody(BaseModel):
    request_type: ReviewRequestType = ReviewRequestType.NOMINAL_IDENTIFICATION_REVIEW


class ExecutiveReviewRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    decision_id: str
    tenant_id: str
    empresa_codigo: str | None = None
    tenant_name: str | None = None
    request_type: ReviewRequestType
    title: str
    description: str
    requested_by: str | None = None
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: ReviewRequestStatus = ReviewRequestStatus.REQUESTED
    priority: str = "NORMAL"
    evidence_item_ids: list[str] = Field(default_factory=list)
    evidence_count: int = 0
    evidence_total_amount: float = 0.0
    identified_count: int = 0
    identified_amount: float = 0.0
    unidentified_count: int = 0
    unidentified_amount: float = 0.0
    review_responsible: str | None = None
    review_responsible_id: str | None = None
    assigned_at: datetime | None = None
    item_checks: dict[str, Any] = Field(default_factory=dict)
    due_date: str | None = None
    resolution_summary: str | None = None
    resolved_at: datetime | None = None
    source_analysis_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    def to_response(self, *, already_exists: bool = False, message: str | None = None) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload["message"] = message or "Conferência solicitada"
        if already_exists:
            payload["already_exists"] = True
        return payload
