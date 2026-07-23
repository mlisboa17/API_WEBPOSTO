"""DIR-01 — endpoints de evidência e solicitação de conferência executiva.

EXEC-02 — endpoints de execução de decisão (Decision Execution Platform):
    POST /{decision_id}/execute  — Owner clica "Executar Agora" (NEW/READY -> EXECUTING)
    POST /{decision_id}/confirm  — Owner confirma resultado (EXECUTING -> COMPLETED/PARTIAL/NOT_COMPLETED)
    GET  /{decision_id}/timeline — Timeline + status atual + impacto estimado/confirmado

EXEC-03 — dashboard de métricas de execução:
    GET  /metrics/summary — Resumo de execução por tenant (pendentes, hoje, período, all-time)
    GET  /metrics/period  — Métricas agregadas de um período (taxas de execução/conclusão, impacto)

FASE 5 (APRENDER) — Behavior Learning:
    GET  /behavior-insights — Quais categorias de decisão o owner mais executa/ignora, motivos de rejeição
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Response
from pydantic import BaseModel

from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService
from src.services.decision_execution import (
    BehaviorAnalyticsService,
    ConfirmationError,
    ConfirmationResult,
    DecisionAction,
    DecisionStatus,
    EstimatedImpact,
    ExecutionError,
    ExecutionMetricsCalculator,
    ExecutionService,
    ImpactType,
    PartialReason,
    RejectionReason,
    SQLExecutionRecordStore,
)
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
_execution_store = SQLExecutionRecordStore()
_execution_service = ExecutionService(repository=_execution_store)
_behavior_analytics_service = BehaviorAnalyticsService()


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


def _total_from_money_found(money_found: dict[str, Any]) -> float:
    total = 0.0
    for bucket in ("at_risk", "recoverable", "additional"):
        entry = money_found.get(bucket) or {}
        try:
            total += float(entry.get("value") or 0)
        except (TypeError, ValueError):
            continue
    return total


def _impact_type_from_money_found(money_found: dict[str, Any]) -> ImpactType:
    buckets = {
        "recoverable": ImpactType.RECOVERED,
        "at_risk": ImpactType.PREVENTED,
        "additional": ImpactType.ADDITIONAL,
    }
    best_bucket = max(
        buckets,
        key=lambda b: float((money_found.get(b) or {}).get("value") or 0),
        default="recoverable",
    )
    return buckets.get(best_bucket, ImpactType.RECOVERED)


async def _get_or_create_execution_record(decision_id: str):
    """Cria o ExecutionRecord (status NEW) na primeira vez que a decisão é executada,
    usando o snapshot de evidência já resolvido pelo DIR-01 como fonte de dados."""
    record = _execution_store.get(decision_id)
    if record:
        return record

    evidence = await _evidence_service.get_evidence(decision_id)
    if not evidence:
        return None

    meta = evidence.source_metadata or {}
    money_found = evidence.money_found or {}
    detector = str(meta.get("detector") or "unknown")
    tenant_id = str(meta.get("tenant_id") or "")
    source_endpoints = meta.get("source_endpoints") or []

    estimated_impact = EstimatedImpact(
        impact_type=_impact_type_from_money_found(money_found),
        amount=Decimal(str(round(_total_from_money_found(money_found), 2))),
        confidence=float(evidence.confidence or 0.8),
        calculation_method=f"{detector} (Decision Discovery Engine)",
        source_engine=detector,
        source_endpoint=source_endpoints[0] if source_endpoints else None,
        display_label="Estimado",
    )

    record = _execution_service.create_decision(
        decision_id=decision_id,
        tenant_id=tenant_id,
        empresa_codigo=tenant_id,
        title=evidence.decision_summary or decision_id,
        category=detector,
        decision_type=detector,
        priority="high",
        action_type=DecisionAction.EXECUTE_NOW,
        estimated_impact=estimated_impact,
        confidence_score=round(float(evidence.confidence or 0.8) * 100, 2),
        source_engine=detector,
        source_endpoint=source_endpoints[0] if source_endpoints else None,
        action_context={"decision_id": decision_id, "tenant_name": meta.get("tenant_name")},
    )
    return _execution_service.present_decision(record)


class ExecuteDecisionBody(BaseModel):
    user_id: str = "owner"


@router.post("/{decision_id}/execute")
async def execute_decision_endpoint(
    decision_id: str,
    body: ExecuteDecisionBody = Body(default_factory=ExecuteDecisionBody),
) -> dict:
    """Owner clica "Executar Agora": cria/avança o ExecutionRecord para EXECUTING."""
    record = await _get_or_create_execution_record(decision_id)
    if not record:
        raise HTTPException(status_code=404, detail="Decisão não encontrada nos snapshots de análise")

    if record.current_status == DecisionStatus.EXECUTING:
        return {"success": True, "data": _execution_service.get_execution_context(record)}

    if record.current_status != DecisionStatus.READY:
        raise HTTPException(
            status_code=409,
            detail=f"Decisão já está em status '{record.current_status.value}', não pode ser reexecutada.",
        )

    try:
        result = _execution_service.execute_decision(record, body.user_id)
    except ExecutionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    result = dict(result)
    result.pop("execution_record", None)
    return {"success": True, "data": result}


class ConfirmDecisionBody(BaseModel):
    user_id: str = "owner"
    result: str  # 'yes' | 'partial' | 'no'
    confirmed_amount: float | None = None
    verification_method: str = "owner_confirmed"
    evidence_ids: list[str] | None = None
    time_spent_minutes: int | None = None
    notes: str | None = None
    partial_progress: float | None = None
    partial_reason: str | None = None
    partial_details: str | None = None
    next_action: str | None = None
    rejection_reason: str | None = None
    rejection_details: str | None = None


@router.post("/{decision_id}/confirm")
async def confirm_decision_endpoint(decision_id: str, body: ConfirmDecisionBody) -> dict:
    """Owner responde 'a decisão resolveu o problema?' (SIM/PARCIALMENTE/NÃO)."""
    record = _execution_store.get(decision_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail="Decisão ainda não foi executada (chame /execute antes de /confirm)",
        )

    try:
        confirmation_result = ConfirmationResult(body.result)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"result inválido: {body.result!r} (use yes/partial/no)") from None

    try:
        confirmed_amount = (
            Decimal(str(body.confirmed_amount)) if body.confirmed_amount is not None else None
        )
    except InvalidOperation:
        raise HTTPException(status_code=422, detail="confirmed_amount inválido") from None

    try:
        record = _execution_service.confirm_result(
            record,
            body.user_id,
            confirmation_result,
            confirmed_amount=confirmed_amount,
            verification_method=body.verification_method,
            evidence_ids=body.evidence_ids,
            time_spent_minutes=body.time_spent_minutes,
            notes=body.notes,
            partial_progress=body.partial_progress,
            partial_reason=PartialReason(body.partial_reason) if body.partial_reason else None,
            partial_details=body.partial_details,
            next_action=body.next_action,
            rejection_reason=RejectionReason(body.rejection_reason) if body.rejection_reason else None,
            rejection_details=body.rejection_details,
        )
    except (ExecutionError, ConfirmationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"success": True, "data": _execution_service.get_execution_context(record)}


@router.get("/{decision_id}/timeline")
async def get_decision_timeline(decision_id: str) -> dict:
    """Timeline completa (status, eventos, impacto estimado/confirmado) de uma decisão."""
    record = _execution_store.get(decision_id)
    if not record:
        raise HTTPException(status_code=404, detail="Decisão ainda não foi executada")
    return {"success": True, "data": _execution_service.get_execution_context(record)}


@router.get("/metrics/summary")
async def get_execution_metrics_summary(tenant_id: str, empresa_codigo: str) -> dict:
    """EXEC-03 — Dashboard de métricas: pendentes, atividade de hoje, período (mês atual) e all-time."""
    records = _execution_store.list_all()
    summary = ExecutionMetricsCalculator.calculate_tenant_summary(
        records, tenant_id=tenant_id, empresa_codigo=empresa_codigo
    )
    return {"success": True, "data": json.loads(summary.model_dump_json())}


@router.get("/metrics/period")
async def get_execution_metrics_period(
    period_start: datetime,
    period_end: datetime,
    tenant_id: str | None = None,
) -> dict:
    """EXEC-03 — Métricas agregadas de um período: taxas de execução/conclusão e impacto estimado vs confirmado."""
    records = _execution_store.list_all()
    metrics = ExecutionMetricsCalculator.calculate_period_metrics(
        records, period_start=period_start, period_end=period_end, tenant_id=tenant_id
    )
    data = json.loads(metrics.model_dump_json())
    data.update(
        {
            "presentation_rate": metrics.presentation_rate,
            "execution_rate": metrics.execution_rate,
            "completion_rate": metrics.completion_rate,
            "success_rate": metrics.success_rate,
            "confirmation_rate": metrics.confirmation_rate,
        }
    )
    return {"success": True, "data": data}


@router.get("/behavior-insights")
async def get_behavior_insights() -> dict:
    """FASE 5 (APRENDER) — quais categorias o owner mais executa/ignora, e motivos de rejeição."""
    records = _execution_store.list_all()
    insights = _behavior_analytics_service.analyze(records)
    return {"success": True, "data": insights}
