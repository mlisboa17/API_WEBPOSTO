"""DIR-01 — endpoints de evidência e solicitação de conferência executiva."""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Response

from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService
from src.services.executive_review.models import CreateReviewRequestBody
from src.services.executive_review.service import (
    DecisionNotFoundError,
    ExecutiveReviewService,
    NoPendingEvidenceError,
)

router = APIRouter(prefix="/api/v1/decisions", tags=["Decisions"])
review_lookup_router = APIRouter(prefix="/api/v1/review-requests", tags=["Executive Review"])

_evidence_service = DecisionEvidenceService()
_review_service = ExecutiveReviewService(_evidence_service)


@router.get("/{decision_id}/evidence")
async def get_decision_evidence(decision_id: str) -> dict:
    """Retorna lançamentos/evidências que sustentam uma decisão prioritária."""
    result = await _evidence_service.get_evidence(decision_id)
    if not result:
        raise HTTPException(status_code=404, detail="Decisão não encontrada nos snapshots de análise")
    return {"success": True, "data": result.model_dump()}


@router.post("/{decision_id}/review-requests", status_code=201)
async def create_decision_review_request(
    decision_id: str,
    response: Response,
    body: CreateReviewRequestBody = Body(default_factory=CreateReviewRequestBody),
) -> dict:
    """Solicita conferência executiva para lançamentos sem identificação nominal."""
    try:
        request, already_exists = await _review_service.create_review_request(decision_id, body)
    except DecisionNotFoundError:
        raise HTTPException(status_code=404, detail="Decisão não encontrada nos snapshots de análise") from None
    except NoPendingEvidenceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if already_exists:
        response.status_code = 200

    data = request.to_response(
        already_exists=already_exists,
        message="Conferência já solicitada" if already_exists else "Conferência solicitada",
    )
    return {"success": True, "data": data}


@router.get("/{decision_id}/review-requests")
async def list_decision_review_requests(decision_id: str) -> dict:
    """Lista solicitações de conferência vinculadas à decisão."""
    try:
        requests = await _review_service.list_for_decision(decision_id)
    except DecisionNotFoundError:
        raise HTTPException(status_code=404, detail="Decisão não encontrada nos snapshots de análise") from None

    return {
        "success": True,
        "data": {
            "decision_id": decision_id,
            "requests": [r.model_dump(mode="json") for r in requests],
            "active": next((r.model_dump(mode="json") for r in requests if r.is_active()), None),
        },
    }


@review_lookup_router.get("/{request_id}")
async def get_review_request(request_id: str) -> dict:
    """Consulta solicitação de conferência por ID."""
    request = _review_service.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Solicitação de conferência não encontrada")
    return {"success": True, "data": request.model_dump(mode="json")}
