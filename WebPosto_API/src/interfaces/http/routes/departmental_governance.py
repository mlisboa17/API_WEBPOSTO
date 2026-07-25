"""Sprints 7 e 8 — alertas, auditoria e operação departamental."""

from fastapi import APIRouter, Depends, HTTPException, Query
from src.interfaces.http.authz import require_roles
from datetime import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.services.departmental_alert_service import DepartmentalAlertService
from src.services.departmental_automation_service import get_departmental_automation
from src.services.departmental_operations_service import DepartmentalOperationsService
from src.services.departmental_schedule_config_service import DepartmentalScheduleConfigService
from src.services.proactive_executive_radar_service import ProactiveExecutiveRadarService
from src.services.proactive_notification_service import ProactiveNotificationService
from src.services.proactive_value_service import ProactiveValueService
from src.services.proactive_agent_orchestrator_service import ProactiveAgentOrchestratorService
from src.services.executive_adoption_service import ExecutiveAdoptionService

router = APIRouter(prefix="/api/v1/departmental-governance", tags=["Departmental Governance"])
_alerts = DepartmentalAlertService()
_operations = DepartmentalOperationsService(alerts=_alerts)
_schedule = DepartmentalScheduleConfigService()
_automation = get_departmental_automation()
_radar = ProactiveExecutiveRadarService(operations=_operations)
_notifications = ProactiveNotificationService()
_value = ProactiveValueService()
_agents = ProactiveAgentOrchestratorService()
_adoption = ExecutiveAdoptionService()


class AlertActionBody(BaseModel):
    justification: str | None = None
    evidence: str | None = None


class DepartmentalScheduleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timezoneName: str
    dailyEnabled: bool
    dailyTime: time
    dailyOffsetDays: int = Field(ge=1, le=7)
    weeklyEnabled: bool
    weeklyWeekday: int = Field(ge=0, le=6)
    weeklyTime: time
    weeklyWindowDays: int = Field(ge=1, le=31)


class RecommendationTransitionBody(BaseModel):
    action: Literal[
        "VIEWED", "ACCEPTED", "REJECTED", "IMPLEMENTED", "VALIDATED",
        "EXECUTED", "CONFIRMED",
    ]
    evidence: str = Field(min_length=3)
    falsePositive: bool = False
    revenueGeneratedBRL: float = Field(default=0, ge=0)
    costAvoidedBRL: float = Field(default=0, ge=0)
    riskMitigatedBRL: float = Field(default=0, ge=0)
    executiveHoursSaved: float = Field(default=0, ge=0)


class ExecutiveAdoptionBody(BaseModel):
    eventType: Literal["PAGE_OPEN", "INFORMATION_FOUND", "FEATURE_USED"]
    feature: Literal["ATTENTION", "VALUE", "AI_VALUE", "PRESIDENCY_ANSWERS", "DETAILS"]
    sessionId: str = Field(min_length=1, max_length=80)
    elapsedMs: int | None = Field(default=None, ge=0, le=3_600_000)
    clicks: int | None = Field(default=None, ge=0, le=100)


def _schedule_payload(config) -> dict:
    payload = config.model_dump(mode="json")
    return {
        "timezoneName": payload["timezone_name"],
        "dailyEnabled": payload["daily_enabled"],
        "dailyTime": payload["daily_time"],
        "dailyOffsetDays": payload["daily_offset_days"],
        "weeklyEnabled": payload["weekly_enabled"],
        "weeklyWeekday": payload["weekly_weekday"],
        "weeklyTime": payload["weekly_time"],
        "weeklyWindowDays": payload["weekly_window_days"],
        "updatedAt": payload["updated_at"],
        "updatedBy": payload["updated_by"],
    }


@router.get("/alerts")
async def departmental_alerts(data: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$")) -> dict:
    return {"success": True, "data": _alerts.list(data), "error": None}


@router.post("/alerts/evaluate")
async def evaluate_departmental_alerts(
    data: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: dict = Depends(require_roles("operations", "director", "audit", "admin", "owner")),
) -> dict:
    return {"success": True, "data": _alerts.evaluate(data), "error": None}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    body: AlertActionBody,
    current_user: dict = Depends(require_roles("operations", "director", "audit", "admin", "owner")),
) -> dict:
    actor = str(current_user.get("sub") or "authenticated-user")
    result = _alerts._store.update(alert_id, "ACKNOWLEDGE", actor, justification=body.justification, evidence=body.evidence)
    if result is None:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    return {"success": True, "data": result, "error": None}


@router.post("/alerts/{alert_id}/close")
async def close_alert(
    alert_id: str,
    body: AlertActionBody,
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    actor = str(current_user.get("sub") or "authenticated-user")
    try:
        result = _alerts._store.update(alert_id, "CLOSE", actor, justification=body.justification, evidence=body.evidence)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    return {"success": True, "data": result, "error": None}


@router.get("/health")
async def departmental_health(data: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")) -> dict:
    return {"success": True, "data": _operations.health(data), "error": None}


@router.get("/daily-report")
async def departmental_daily_report(data: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$")) -> dict:
    return {"success": True, "data": _operations.daily_report(data), "error": None}


@router.get("/proactive-radar")
async def proactive_executive_radar(
    data: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    result = _radar.get(data) if data else _radar.latest()
    if not result:
        raise HTTPException(status_code=404, detail="Radar proativo ainda não gerado")
    return {"success": True, "data": result, "error": None}


@router.get("/proactive-notifications")
async def proactive_notifications(
    audience: Literal["PRESIDENT", "DIRECTOR"] | None = None,
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    return {"success": True, "data": _notifications.list(audience), "error": None}


@router.get("/proactive-agents")
async def proactive_agents(
    data: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    result = _agents.get(data) if data else _agents.latest()
    if not result:
        raise HTTPException(status_code=404, detail="Parecer dos agentes ainda não gerado")
    return {"success": True, "data": result, "error": None}


@router.get("/proactive-value")
async def proactive_value(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    return {
        "success": True,
        "data": {"summary": _value.summary(month), "recommendations": _value.list(month)},
        "error": None,
    }


@router.post("/executive-adoption/events")
async def record_executive_adoption(
    body: ExecutiveAdoptionBody,
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    return {"success": True, "data": _adoption.record(body.model_dump()), "error": None}


@router.get("/executive-adoption/summary")
async def executive_adoption_summary(
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    return {"success": True, "data": _adoption.summary(), "error": None}


@router.post("/proactive-value/{recommendation_id}/transition")
async def transition_proactive_recommendation(
    recommendation_id: str,
    body: RecommendationTransitionBody,
    current_user: dict = Depends(require_roles("director", "audit", "admin", "owner")),
) -> dict:
    actor = str(current_user.get("sub") or "authenticated-user")
    canonical_action = {
        "EXECUTED": "IMPLEMENTED",
        "CONFIRMED": "VALIDATED",
    }.get(body.action, body.action)
    if canonical_action == "VALIDATED" and str(current_user.get("role", "")).lower() not in {
        "audit", "admin", "owner",
    }:
        raise HTTPException(status_code=403, detail="Validação de resultado exige perfil independente")
    confirmed = {
        "revenueGeneratedBRL": body.revenueGeneratedBRL,
        "costAvoidedBRL": body.costAvoidedBRL,
        "riskMitigatedBRL": body.riskMitigatedBRL,
        "executiveHoursSaved": body.executiveHoursSaved,
    } if canonical_action == "VALIDATED" else None
    try:
        result = _value.transition(
            recommendation_id, canonical_action, actor, body.evidence, confirmed,
            body.falsePositive,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not result:
        raise HTTPException(status_code=404, detail="Recomendação não encontrada")
    return {"success": True, "data": result, "error": None}


@router.get("/weekly-report")
async def departmental_weekly_report(dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$")) -> dict:
    return {"success": True, "data": _operations.weekly_report(dataFinal), "error": None}


@router.get("/schedule")
async def get_departmental_schedule() -> dict:
    return {"success": True, "data": _schedule_payload(_schedule.get()), "error": None}


@router.put("/schedule")
async def update_departmental_schedule(
    body: DepartmentalScheduleBody,
    current_user: dict = Depends(require_roles("operations", "director", "admin", "owner")),
) -> dict:
    actor = str(current_user.get("sub") or "authenticated-user")
    try:
        config = _schedule.update(
            {
                "timezone_name": body.timezoneName,
                "daily_enabled": body.dailyEnabled,
                "daily_time": body.dailyTime,
                "daily_offset_days": body.dailyOffsetDays,
                "weekly_enabled": body.weeklyEnabled,
                "weekly_weekday": body.weeklyWeekday,
                "weekly_time": body.weeklyTime,
                "weekly_window_days": body.weeklyWindowDays,
            },
            actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"success": True, "data": _schedule_payload(config), "error": None}


@router.post("/schedule/run-due")
async def run_due_departmental_schedule(
    current_user: dict = Depends(require_roles("operations", "admin", "owner")),
) -> dict:
    return {"success": True, "data": await _automation.run_due(), "error": None}


@router.get("/schedule/history")
async def departmental_schedule_history() -> dict:
    return {"success": True, "data": _automation.history(), "error": None}
