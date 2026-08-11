from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Literal

from src.services.cash_reconciliation.cash_exposure_service import CashExposureService
from src.services.cash_reconciliation.cash_reconciliation_service import CashReconciliationService
from src.services.cash_reconciliation.cash_reconciliation_snapshot_service import CashReconciliationSnapshotService
from src.services.payment_method_catalog_service import PaymentMethodCatalogService

router = APIRouter(prefix="/api/v1/cash-reconciliation", tags=["Cash Reconciliation"])

_service = CashReconciliationService()
_snapshot = CashReconciliationSnapshotService(_service)
_payment_methods = PaymentMethodCatalogService()
_exposure = CashExposureService(_service)


class JustifyBody(BaseModel):
    itemId: str
    reasonCategory: str
    description: str = Field(min_length=3)
    responsibleUser: str
    expectedResolutionDate: str | None = None


class ConfirmBody(BaseModel):
    itemId: str
    user: str | None = None


class CashDestinationBody(BaseModel):
    dataInicial: str
    dataFinal: str
    empresaCodigo: str
    movementDate: str
    destination: Literal["BANCO", "COFRE", "TESOURARIA", "FUNDO_CAIXA", "DESPESA_SANGRIA", "NAO_DEPOSITADO", "OUTRO"]
    amount: float = Field(ge=0)
    destinationDate: str | None = None
    bankAccount: str | None = None
    bankMovementCode: str | None = None
    reference: str | None = None
    responsibleUser: str = Field(min_length=2)
    note: str | None = None


@router.get("/cash-destinations")
async def cash_destinations(
    dataInicial: str = Query(...), dataFinal: str = Query(...), empresaCodigo: str = Query(...),
) -> dict:
    key = _service._state.state_key(empresaCodigo, dataInicial, dataFinal)
    return {"success": True, "data": _service._state.list_cash_destinations(key)}


@router.post("/cash-destinations")
async def save_cash_destination(body: CashDestinationBody) -> dict:
    key = _service._state.state_key(body.empresaCodigo, body.dataInicial, body.dataFinal)
    record = _service._state.set_cash_destination(
        key, body.empresaCodigo, body.movementDate, body.model_dump(exclude={"dataInicial", "dataFinal", "empresaCodigo", "movementDate"}),
    )
    return {"success": True, "data": record}


@router.get("/payment-methods")
async def payment_methods(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str = Query(...),
) -> dict:
    return {"success": True, "data": await _payment_methods.build(dataInicial, dataFinal, empresaCodigo)}


@router.get("/summary")
async def reconciliation_summary(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        raise HTTPException(status_code=502, detail="Falha ao consolidar conferência financeira")
    return {"success": True, "data": payload, "snapshot": {"hit": hit, "stale": stale}}


@router.get("/cash-exposure")
async def cash_closing_exposure(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: str | None = Query(
        None, description="Código da empresa/posto (obrigatório para leitura útil)."
    ),
) -> dict:
    """CASH-01 — Divergência de fechamento (Apresentado × Apurado). Escopo: CASH_CLOSING.

    Não afirma liquidação bancária, EDI, recebível adquirente ou perda confirmada.
    """
    dto = await _exposure.build(dataInicial, dataFinal, empresaCodigo)
    return {"success": True, "data": dto.model_dump()}


@router.get("/exceptions")
async def reconciliation_exceptions(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        raise HTTPException(status_code=502, detail="Falha ao listar exceções")
    return {
        "success": True,
        "data": payload.get("exceptions") or [],
        "preCheck": (payload.get("summary") or {}).get("preCheck"),
        "snapshot": {"hit": hit, "stale": stale},
    }


@router.get("/audit-signals")
async def reconciliation_audit_signals(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        raise HTTPException(status_code=502, detail="Falha ao gerar sinais de auditoria")
    signals = (payload.get("summary") or {}).get("auditSignals") or []
    return {"success": True, "data": signals, "snapshot": {"hit": hit, "stale": stale}}


@router.post("/justify")
async def reconciliation_justify(
    body: JustifyBody,
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _service.justify_item(
        dataInicial,
        dataFinal,
        empresaCodigo,
        body.itemId,
        body.reasonCategory,
        body.description,
        body.responsibleUser,
        body.expectedResolutionDate,
    )
    _snapshot._store.delete(_snapshot.master_key(dataInicial, dataFinal, empresaCodigo))
    return result


@router.post("/confirm")
async def reconciliation_confirm(
    body: ConfirmBody,
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    result = await _service.confirm_item(
        dataInicial,
        dataFinal,
        empresaCodigo,
        body.itemId,
        body.user,
    )
    _snapshot._store.delete(_snapshot.master_key(dataInicial, dataFinal, empresaCodigo))
    return result


@router.get("/parity")
async def reconciliation_parity(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str = Query(...),
) -> dict:
    """Paridade operacional — valores de referência ficam no script QA, não na aplicação."""
    report = await _service.parity_report(dataInicial, dataFinal, empresaCodigo, reference=None)
    return report
