"""Router isolado de DRAFTs de despesa. Montado só no demo_app; não montar em app.py."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from src.interfaces.http.authz import require_roles
from src.services.executive_copilot.action_proposals import _parse_money, _expense_desc
from src.services.executive_copilot.expense_drafts import ExpenseDraftService
from src.services.executive_copilot.unit_capabilities import select_requested_units
from src.services.sds_sanitize import sanitize_value

router = APIRouter(prefix="/api/v1/executive-copilot/action-drafts", tags=["Executive Copilot Action Drafts"])

_ROLES = ("director", "admin", "owner", "manager")
_service: ExpenseDraftService | None = None
_factory: Callable[[], ExpenseDraftService] | None = None


class SaveExpenseDraftBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    question: str | None = Field(None, alias="pergunta")
    units: list[int] | None = Field(None, alias="unidades")
    unit_public_name: str | None = Field(None, alias="unitPublicName")
    valor: float | None = None
    descricao: str | None = None


def configure_expense_drafts(
    service: ExpenseDraftService | None = None,
    *,
    factory: Any = None,
) -> ExpenseDraftService | None:
    global _service, _factory
    _service = service
    _factory = factory
    return _service


def get_expense_draft_service() -> ExpenseDraftService:
    global _service
    if _service is None:
        if _factory is None:
            raise RuntimeError("ExpenseDraftService não configurado")
        _service = _factory()
    return _service


def _resolve_save(body: SaveExpenseDraftBody) -> tuple[int | None, float | None, str, bool]:
    question = body.question or ""
    selection = select_requested_units(
        " ".join(part for part in [question, body.unit_public_name or ""] if part),
        body.units,
    )
    amount = body.valor
    if amount is None and question:
        parsed, invalid = _parse_money(question)
        amount = None if invalid else parsed
    descricao = (body.descricao or "").strip() or _expense_desc(question)
    unit = selection.codes[0] if len(selection.codes) == 1 else None
    return unit, amount, descricao, selection.all_units


@router.post("/expenses")
async def save_expense_draft(
    body: SaveExpenseDraftBody,
    current_user: dict = Depends(require_roles(*_ROLES)),
    service: ExpenseDraftService = Depends(get_expense_draft_service),
) -> dict[str, Any]:
    unit, valor, descricao, todas = _resolve_save(body)
    return sanitize_value(
        service.save(user=current_user, unit=unit, valor=valor, descricao=descricao, all_units=todas)
    )


@router.get("/{draft_id}")
async def get_expense_draft(
    draft_id: str,
    current_user: dict = Depends(require_roles(*_ROLES)),
    service: ExpenseDraftService = Depends(get_expense_draft_service),
) -> dict[str, Any]:
    return sanitize_value(service.get(draft_id, current_user))


@router.post("/{draft_id}/confirm")
async def confirm_expense_draft(
    draft_id: str,
    current_user: dict = Depends(require_roles(*_ROLES)),
    service: ExpenseDraftService = Depends(get_expense_draft_service),
) -> dict[str, Any]:
    return sanitize_value(service.confirm(draft_id, current_user))


@router.post("/{draft_id}/approve")
async def approve_expense_draft(
    draft_id: str,
    current_user: dict = Depends(require_roles(*_ROLES)),
    service: ExpenseDraftService = Depends(get_expense_draft_service),
) -> dict[str, Any]:
    return sanitize_value(service.approve(draft_id, current_user))


@router.post("/{draft_id}/reject")
async def reject_expense_draft(
    draft_id: str,
    current_user: dict = Depends(require_roles(*_ROLES)),
    service: ExpenseDraftService = Depends(get_expense_draft_service),
) -> dict[str, Any]:
    return sanitize_value(service.reject(draft_id, current_user))


@router.post("/{draft_id}/cancel")
async def cancel_expense_draft(
    draft_id: str,
    current_user: dict = Depends(require_roles(*_ROLES)),
    service: ExpenseDraftService = Depends(get_expense_draft_service),
) -> dict[str, Any]:
    return sanitize_value(service.cancel(draft_id, current_user))


@router.post("/{draft_id}/execute")
async def execute_expense_draft(
    draft_id: str,
    current_user: dict = Depends(require_roles(*_ROLES)),
    service: ExpenseDraftService = Depends(get_expense_draft_service),
) -> dict[str, Any]:
    return sanitize_value(service.execute(draft_id, current_user))
