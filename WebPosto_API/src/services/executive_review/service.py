"""DIR-01D — criação e consulta de solicitações de conferência executiva."""

from __future__ import annotations

from datetime import datetime, timezone

from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService
from src.services.decision_evidence.models import DecisionEvidenceItem
from src.services.executive_review.models import (
    CreateReviewRequestBody,
    ExecutiveReviewRequest,
    ReviewRequestStatus,
    ReviewRequestType,
)
from src.services.executive_review.pending_evidence import item_needs_nominal_review, partition_evidence_items
from src.services.executive_review.store import ExecutiveReviewStore


class DecisionNotFoundError(LookupError):
    pass


class NoPendingEvidenceError(ValueError):
    pass


class ExecutiveReviewService:
    REQUESTED_BY_CONTEXT = None

    def __init__(
        self,
        evidence_service: DecisionEvidenceService | None = None,
        store: ExecutiveReviewStore | None = None,
    ) -> None:
        self._evidence = evidence_service or DecisionEvidenceService()
        self._store = store or ExecutiveReviewStore()

    async def create_review_request(
        self,
        decision_id: str,
        body: CreateReviewRequestBody | None = None,
    ) -> tuple[ExecutiveReviewRequest, bool]:
        body = body or CreateReviewRequestBody()
        evidence = await self._evidence.get_evidence(decision_id)
        if not evidence:
            raise DecisionNotFoundError(decision_id)

        existing = self._store.find_active(decision_id, body.request_type)
        if existing:
            return existing, True

        pending = [i for i in evidence.evidence_items if item_needs_nominal_review(i)]
        if not pending:
            raise NoPendingEvidenceError(
                "Nenhum lançamento pendente de identificação nominal para solicitar conferência."
            )

        identified, _ = partition_evidence_items(evidence.evidence_items)
        tenant_id = str(evidence.source_metadata.get("tenant_id") or "")
        meta = evidence.source_metadata or {}
        pending_amount = round(sum(i.amount for i in pending), 2)
        identified_amount = round(sum(i.amount for i in identified), 2)

        request = ExecutiveReviewRequest(
            decision_id=decision_id,
            tenant_id=tenant_id,
            empresa_codigo=str(meta.get("tenant_id") or tenant_id or ""),
            tenant_name=meta.get("tenant_name"),
            request_type=body.request_type,
            title=f"Conferência nominal — {len(pending)} lançamento(s)",
            description=(
                f"{len(pending)} lançamento(s) desta decisão (R$ {pending_amount:,.2f}) "
                "requerem validação de beneficiário nas fontes disponíveis."
            ),
            requested_by=self.REQUESTED_BY_CONTEXT,
            status=ReviewRequestStatus.REQUESTED,
            evidence_item_ids=[i.id for i in pending],
            evidence_count=len(pending),
            evidence_total_amount=pending_amount,
            identified_count=len(identified),
            identified_amount=identified_amount,
            unidentified_count=len(pending),
            unidentified_amount=pending_amount,
            review_responsible=None,
            review_responsible_id=None,
            source_analysis_id=decision_id,
            requested_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._store.save(request)
        return request, False

    async def list_for_decision(self, decision_id: str) -> list[ExecutiveReviewRequest]:
        evidence = await self._evidence.get_evidence(decision_id)
        if not evidence:
            raise DecisionNotFoundError(decision_id)
        return self._store.list_by_decision(decision_id)

    def get_request(self, request_id: str) -> ExecutiveReviewRequest | None:
        return self._store.get(request_id)

    @staticmethod
    def pending_summary(items: list[DecisionEvidenceItem]) -> dict[str, float | int]:
        pending = [i for i in items if item_needs_nominal_review(i)]
        identified = [i for i in items if i.person_name and not item_needs_nominal_review(i)]
        return {
            "total_count": len(items),
            "pending_count": len(pending),
            "pending_amount": round(sum(i.amount for i in pending), 2),
            "identified_count": len(identified),
            "identified_amount": round(sum(i.amount for i in identified), 2),
        }
