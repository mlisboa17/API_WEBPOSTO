"""DIR-02 — projeção ExecutiveFollowUpItem (sem persistência duplicada)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService
from src.services.executive_review.models import (
    ACTIVE_STATUSES,
    ExecutiveReviewRequest,
    ReviewRequestStatus,
    ReviewRequestType,
)
from src.services.executive_review.status_labels import (
    PRIORITY_RANK,
    request_type_label,
    status_label,
)
from src.services.executive_review.store import ExecutiveReviewStore


class ExecutiveFollowUpItem(BaseModel):
    id: str
    request_id: str
    decision_id: str
    tenant_id: str
    empresa_codigo: str | None = None
    tenant_name: str | None = None
    request_type: str
    title: str
    description: str
    status: str
    status_label: str
    priority: str = "NORMAL"
    evidence_count: int = 0
    evidence_total_amount: float = 0.0
    requested_at: str
    review_responsible: str | None = None
    decision_title: str | None = None
    decision_category: str | None = None
    source_analysis_id: str | None = None
    request_type_label: str | None = None
    checked_items_count: int = 0
    total_items_count: int = 0
    item_progress_percent: float = 0.0


class FollowUpSummary(BaseModel):
    active_count: int = 0
    total_amount_in_review: float = 0.0
    awaiting_assignment_count: int = 0
    in_review_count: int = 0


class ExecutiveFollowUpService:
    def __init__(
        self,
        store: ExecutiveReviewStore | None = None,
        evidence_service: DecisionEvidenceService | None = None,
    ) -> None:
        self._store = store or ExecutiveReviewStore()
        self._evidence = evidence_service or DecisionEvidenceService()
        self._decision_cache: dict[str, dict[str, Any]] = {}

    def _decision_meta(self, decision_id: str) -> dict[str, Any]:
        if decision_id in self._decision_cache:
            return self._decision_cache[decision_id]
        candidate = self._evidence._find_candidate(decision_id) or {}
        evidence = candidate.get("evidence") or {}
        meta = {
            "decision_title": candidate.get("title") or candidate.get("summary"),
            "decision_category": evidence.get("category") or evidence.get("label"),
        }
        self._decision_cache[decision_id] = meta
        return meta

    def to_follow_up_item(self, request: ExecutiveReviewRequest) -> ExecutiveFollowUpItem:
        meta = self._decision_meta(request.decision_id)
        total_items = len(request.evidence_item_ids) or int(request.evidence_count or 0)
        checked_items = len(request.item_checks or {})
        progress = round((checked_items / total_items) * 100, 2) if total_items else 0.0
        return ExecutiveFollowUpItem(
            id=request.id,
            request_id=request.id,
            decision_id=request.decision_id,
            tenant_id=request.tenant_id,
            empresa_codigo=request.empresa_codigo,
            tenant_name=request.tenant_name,
            request_type=request.request_type.value,
            title=request.title,
            description=request.description,
            status=request.status.value,
            status_label=status_label(request.status),
            priority=request.priority,
            evidence_count=request.evidence_count,
            evidence_total_amount=request.evidence_total_amount,
            requested_at=request.requested_at.isoformat(),
            review_responsible=request.review_responsible,
            decision_title=meta.get("decision_title"),
            decision_category=meta.get("decision_category"),
            source_analysis_id=request.source_analysis_id,
            request_type_label=request_type_label(request.request_type),
            checked_items_count=checked_items,
            total_items_count=total_items,
            item_progress_percent=progress,
        )

    def list_follow_ups(
        self,
        *,
        status: str | None = None,
        tenant_id: str | None = None,
        request_type: str | None = None,
        active_only: bool = True,
    ) -> tuple[list[ExecutiveFollowUpItem], FollowUpSummary]:
        requests = self._store.list_all()
        filtered: list[ExecutiveReviewRequest] = []

        for req in requests:
            if active_only and req.status not in ACTIVE_STATUSES:
                continue
            if status and req.status.value != status:
                continue
            if tenant_id and str(req.tenant_id) != str(tenant_id):
                continue
            if request_type and req.request_type.value != request_type:
                continue
            filtered.append(req)

        filtered.sort(
            key=lambda r: (
                PRIORITY_RANK.get(str(r.priority or "NORMAL").upper(), 99),
                -float(r.evidence_total_amount or 0),
                r.requested_at,
            )
        )

        items = [self.to_follow_up_item(r) for r in filtered]
        summary = FollowUpSummary(
            active_count=len(items),
            total_amount_in_review=round(sum(i.evidence_total_amount for i in items), 2),
            awaiting_assignment_count=sum(
                1 for i in items if i.status == ReviewRequestStatus.REQUESTED.value
            ),
            in_review_count=sum(
                1
                for i in items
                if i.status
                in {
                    ReviewRequestStatus.IN_REVIEW.value,
                    ReviewRequestStatus.ASSIGNED.value,
                    ReviewRequestStatus.NEEDS_INFORMATION.value,
                }
            ),
        )
        return items, summary

    def get_follow_up(self, request_id: str) -> ExecutiveFollowUpItem | None:
        request = self._store.get(request_id)
        if not request:
            return None
        return self.to_follow_up_item(request)
