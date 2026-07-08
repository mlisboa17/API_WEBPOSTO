"""FIN-01 — projeção FinancialReviewInboxItem (mesma ExecutiveReviewRequest, visão Financeiro)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService
from src.services.decision_evidence.models import DecisionEvidenceItem
from src.services.executive_review.models import (
    ACTIVE_STATUSES,
    ExecutiveReviewRequest,
    ReviewRequestStatus,
)
from src.services.executive_review.status_labels import (
    PRIORITY_RANK,
    financial_status_label,
    request_type_label,
)
from src.services.executive_review.store import ExecutiveReviewStore


class FinancialReviewInboxItem(BaseModel):
    request_id: str
    decision_id: str
    tenant_id: str
    empresa_codigo: str | None = None
    tenant_name: str | None = None
    decision_title: str | None = None
    decision_category: str | None = None
    request_type: str
    request_type_label: str | None = None
    reason: str
    evidence_items_count: int = 0
    amount_under_review: float = 0.0
    requested_at: str
    waiting_since: str
    waiting_time_seconds: int = 0
    technical_status: str
    financial_status_label: str
    review_responsible: str | None = None
    priority: str | None = None


class FinancialReviewInboxSummary(BaseModel):
    active_count: int = 0
    total_amount_under_review: float = 0.0
    awaiting_analysis_count: int = 0
    assigned_count: int = 0


class FinancialReviewPendingEvidenceItem(BaseModel):
    id: str
    date: str | None = None
    description: str | None = None
    amount: float = 0.0
    person_name: str | None = None
    origin: str | None = None
    source: str | None = None
    match_status: str | None = None
    document_reference: str | None = None


class FinancialReviewInboxDetail(FinancialReviewInboxItem):
    origin_label: str = "Decisão da Diretoria"
    pending_evidence_items: list[FinancialReviewPendingEvidenceItem] = Field(default_factory=list)


class FinancialReviewInboxService:
    """Projeção read-only sobre ExecutiveReviewStore — sem persistência duplicada."""

    def __init__(
        self,
        store: ExecutiveReviewStore | None = None,
        evidence_service: DecisionEvidenceService | None = None,
    ) -> None:
        self._store = store or ExecutiveReviewStore()
        self._evidence = evidence_service or DecisionEvidenceService()
        self._decision_cache: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _waiting_seconds(requested_at: datetime) -> int:
        now = datetime.now(timezone.utc)
        if requested_at.tzinfo is None:
            requested_at = requested_at.replace(tzinfo=timezone.utc)
        return max(0, int((now - requested_at).total_seconds()))

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

    def to_inbox_item(self, request: ExecutiveReviewRequest) -> FinancialReviewInboxItem:
        meta = self._decision_meta(request.decision_id)
        waiting = self._waiting_seconds(request.requested_at)
        priority = str(request.priority).strip() if request.priority else None
        return FinancialReviewInboxItem(
            request_id=request.id,
            decision_id=request.decision_id,
            tenant_id=request.tenant_id,
            empresa_codigo=request.empresa_codigo,
            tenant_name=request.tenant_name,
            decision_title=meta.get("decision_title"),
            decision_category=meta.get("decision_category"),
            request_type=request.request_type.value,
            request_type_label=request_type_label(request.request_type),
            reason=request.description,
            evidence_items_count=request.evidence_count,
            amount_under_review=round(float(request.evidence_total_amount or 0), 2),
            requested_at=request.requested_at.isoformat(),
            waiting_since=request.requested_at.isoformat(),
            waiting_time_seconds=waiting,
            technical_status=request.status.value,
            financial_status_label=financial_status_label(request.status),
            review_responsible=request.review_responsible,
            priority=priority,
        )

    def _pending_items_for_request(
        self,
        request: ExecutiveReviewRequest,
        all_items: list[DecisionEvidenceItem],
    ) -> list[FinancialReviewPendingEvidenceItem]:
        if not request.evidence_item_ids:
            return []
        by_id = {item.id: item for item in all_items}
        pending: list[FinancialReviewPendingEvidenceItem] = []
        for item_id in request.evidence_item_ids:
            item = by_id.get(item_id)
            if not item:
                continue
            pending.append(
                FinancialReviewPendingEvidenceItem(
                    id=item.id,
                    date=item.date,
                    description=item.description,
                    amount=item.amount,
                    person_name=item.person_name,
                    origin=item.origin,
                    source=item.source,
                    match_status=item.match_status,
                    document_reference=item.document_reference,
                )
            )
        return pending

    async def get_inbox_detail(self, request_id: str) -> FinancialReviewInboxDetail | None:
        request = self._store.get(request_id)
        if not request:
            return None
        base = self.to_inbox_item(request)
        evidence_response = await self._evidence.get_evidence(
            request.decision_id,
            enrich_nominal=False,
        )
        pending_items: list[FinancialReviewPendingEvidenceItem] = []
        if evidence_response:
            pending_items = self._pending_items_for_request(
                request,
                evidence_response.evidence_items,
            )
        return FinancialReviewInboxDetail(
            **base.model_dump(),
            pending_evidence_items=pending_items,
        )

    def list_inbox(
        self,
        *,
        status: str | None = None,
        tenant_id: str | None = None,
        request_type: str | None = None,
        active_only: bool = True,
    ) -> tuple[list[FinancialReviewInboxItem], FinancialReviewInboxSummary]:
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

        items = [self.to_inbox_item(r) for r in filtered]
        summary = FinancialReviewInboxSummary(
            active_count=len(items),
            total_amount_under_review=round(
                sum(i.amount_under_review for i in items),
                2,
            ),
            awaiting_analysis_count=sum(
                1 for i in items if i.technical_status == ReviewRequestStatus.REQUESTED.value
            ),
            assigned_count=sum(
                1 for i in items if i.technical_status == ReviewRequestStatus.ASSIGNED.value
            ),
        )
        return items, summary

    def get_inbox_item(self, request_id: str) -> FinancialReviewInboxItem | None:
        request = self._store.get(request_id)
        if not request:
            return None
        return self.to_inbox_item(request)
