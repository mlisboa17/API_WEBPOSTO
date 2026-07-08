"""FIN-01/02 — caixa de trabalho financeira (ExecutiveReviewRequest, visão Financeiro)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.services.executive_review.assignment import (
    AssignReviewBody,
    ExecutiveReviewAssignmentService,
    ReviewAssignmentConflictError,
    ReviewAssignmentNotAllowedError,
    ReviewRequestNotFoundError,
)
from src.services.executive_review.financial_inbox import FinancialReviewInboxService

router = APIRouter(prefix="/api/v1/financial", tags=["Financial Review Inbox"])
_service = FinancialReviewInboxService()
_assignment = ExecutiveReviewAssignmentService()


@router.get("/review-inbox")
async def list_financial_review_inbox(
    status: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    request_type: str | None = Query(default=None),
) -> dict:
    """Lista solicitações da Diretoria aguardando análise financeira."""
    items, summary = _service.list_inbox(
        status=status,
        tenant_id=tenant_id,
        request_type=request_type,
        active_only=True,
    )
    return {
        "success": True,
        "data": {
            "items": [item.model_dump() for item in items],
            "summary": summary.model_dump(),
        },
    }


@router.get("/review-inbox/{request_id}")
async def get_financial_review_inbox_detail(request_id: str) -> dict:
    """Detalhe financeiro de uma solicitação de conferência."""
    detail = await _service.get_inbox_detail(request_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    return {"success": True, "data": detail.model_dump()}


@router.post("/review-inbox/{request_id}/assign")
async def assign_financial_review(request_id: str, body: AssignReviewBody) -> dict:
    """FIN-02 — Financeiro assume responsabilidade pela conferência."""
    try:
        request, idempotent = _assignment.assign(request_id, body)
    except ReviewRequestNotFoundError:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada") from None
    except ReviewAssignmentConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ReviewAssignmentNotAllowedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = _assignment.to_result(request, idempotent=idempotent)
    message = (
        "Conferência já estava atribuída a este responsável."
        if idempotent
        else "Conferência atribuída com sucesso."
    )
    return {"success": True, "data": result.model_dump(), "message": message}
