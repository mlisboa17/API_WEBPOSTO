"""Labels executivos para status técnicos de ExecutiveReviewRequest."""

from __future__ import annotations

from src.services.executive_review.models import ReviewRequestStatus, ReviewRequestType

STATUS_EXECUTIVE_LABELS: dict[ReviewRequestStatus, str] = {
    ReviewRequestStatus.REQUESTED: "Aguardando atribuição",
    ReviewRequestStatus.ASSIGNED: "Responsável definido",
    ReviewRequestStatus.IN_REVIEW: "Em conferência",
    ReviewRequestStatus.NEEDS_INFORMATION: "Informação necessária",
    ReviewRequestStatus.COMPLETED: "Conferência concluída",
    ReviewRequestStatus.CANCELLED: "Cancelado",
}

REQUEST_TYPE_LABELS: dict[ReviewRequestType, str] = {
    ReviewRequestType.NOMINAL_IDENTIFICATION_REVIEW: "Conferência de identificação nominal",
}

PRIORITY_RANK: dict[str, int] = {
    "CRITICAL": 0,
    "HIGH": 1,
    "NORMAL": 2,
    "LOW": 3,
}


def status_label(status: ReviewRequestStatus | str | None) -> str:
    if isinstance(status, ReviewRequestStatus):
        return STATUS_EXECUTIVE_LABELS.get(status, str(status.value))
    try:
        parsed = ReviewRequestStatus(str(status))
        return STATUS_EXECUTIVE_LABELS.get(parsed, str(status))
    except ValueError:
        return str(status or "—")


def request_type_label(request_type: ReviewRequestType | str | None) -> str:
    if isinstance(request_type, ReviewRequestType):
        return REQUEST_TYPE_LABELS.get(request_type, request_type.value)
    try:
        parsed = ReviewRequestType(str(request_type))
        return REQUEST_TYPE_LABELS.get(parsed, str(request_type))
    except ValueError:
        return str(request_type or "—")
