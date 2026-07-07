"""DIR-02 — acompanhamento executivo de solicitações de conferência."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.services.executive_review.follow_up import ExecutiveFollowUpService

router = APIRouter(prefix="/api/v1/executive", tags=["Executive Follow-Up"])
_service = ExecutiveFollowUpService()


@router.get("/follow-ups")
async def list_executive_follow_ups(
    status: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    request_type: str | None = Query(default=None),
) -> dict:
    """Lista solicitações executivas ativas para acompanhamento da Diretoria."""
    items, summary = _service.list_follow_ups(
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


@router.get("/follow-ups/{request_id}")
async def get_executive_follow_up(request_id: str) -> dict:
    """Detalhe executivo de uma solicitação em acompanhamento."""
    item = _service.get_follow_up(request_id)
    if not item:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    return {"success": True, "data": item.model_dump()}
