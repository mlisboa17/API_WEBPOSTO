"""FIN-02 — assumir responsabilidade sobre ExecutiveReviewRequest."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from src.services.executive_review.models import ExecutiveReviewRequest, ReviewRequestStatus
from src.services.executive_review.store import ExecutiveReviewStore


class AssignReviewBody(BaseModel):
    responsible_name: str = Field(min_length=1, max_length=200)


class ReviewAssignmentResult(BaseModel):
    request_id: str
    decision_id: str
    tenant_id: str
    status: str
    review_responsible: str
    assigned_at: str
    updated_at: str
    idempotent: bool = False
    financial_status_label: str
    executive_status_label: str


class ReviewRequestNotFoundError(LookupError):
    pass


class ReviewAssignmentNotAllowedError(ValueError):
    pass


class ReviewAssignmentConflictError(ValueError):
    pass


class ExecutiveReviewAssignmentService:
    """Transição REQUESTED → ASSIGNED sobre a mesma persistência."""

    def __init__(self, store: ExecutiveReviewStore | None = None) -> None:
        self._store = store or ExecutiveReviewStore()

    @staticmethod
    def _normalize_name(name: str) -> str:
        cleaned = " ".join(str(name or "").split())
        if not cleaned:
            raise ValueError("responsible_name não pode ser vazio")
        return cleaned

    def assign(
        self,
        request_id: str,
        body: AssignReviewBody,
    ) -> tuple[ExecutiveReviewRequest, bool]:
        responsible_name = self._normalize_name(body.responsible_name)
        outcome: dict[str, bool] = {"idempotent": False}

        def _mutate(request: ExecutiveReviewRequest) -> ExecutiveReviewRequest:
            now = datetime.now(timezone.utc)

            if request.status == ReviewRequestStatus.REQUESTED:
                request.status = ReviewRequestStatus.ASSIGNED
                request.review_responsible = responsible_name
                request.assigned_at = now
                request.updated_at = now
                return request

            if request.status == ReviewRequestStatus.ASSIGNED:
                if request.review_responsible == responsible_name:
                    outcome["idempotent"] = True
                    return request
                raise ReviewAssignmentConflictError(
                    f"Solicitação já atribuída a {request.review_responsible!r}"
                )

            raise ReviewAssignmentNotAllowedError(
                f"Status {request.status.value} não permite assumir conferência"
            )

        try:
            request = self._store.update(request_id, _mutate)
        except KeyError as exc:
            raise ReviewRequestNotFoundError(request_id) from exc

        return request, outcome["idempotent"]

    def to_result(self, request: ExecutiveReviewRequest, *, idempotent: bool) -> ReviewAssignmentResult:
        from src.services.executive_review.status_labels import financial_status_label, status_label

        assigned_at = request.assigned_at or request.updated_at
        return ReviewAssignmentResult(
            request_id=request.id,
            decision_id=request.decision_id,
            tenant_id=request.tenant_id,
            status=request.status.value,
            review_responsible=str(request.review_responsible or ""),
            assigned_at=assigned_at.isoformat(),
            updated_at=request.updated_at.isoformat(),
            idempotent=idempotent,
            financial_status_label=financial_status_label(request.status),
            executive_status_label=status_label(request.status),
        )
