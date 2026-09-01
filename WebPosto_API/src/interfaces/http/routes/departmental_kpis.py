"""Sprint 3 — API de KPIs e DRE departamental."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from src.interfaces.http.authz import require_roles

from src.services.departmental_kpi_service import DepartmentalKpiService
from src.services.departmental_comparison_service import DepartmentalComparisonService
from src.services.departmental_executive_service import DepartmentalExecutiveService
from src.services.departmental_history_service import DepartmentalHistoryService
from src.services.departmental_goal_service import DepartmentalGoalService
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/v1/departmental-kpis",
    tags=["Departmental KPIs Sprint 3"],
)

_service = DepartmentalKpiService()
_comparison = DepartmentalComparisonService(_service)
_history = DepartmentalHistoryService(kpis=_service)
_executive = DepartmentalExecutiveService(_service, _comparison, _history)
_goals = DepartmentalGoalService()


class DepartmentalGoalBody(BaseModel):
    companyCode: int
    department: str
    metric: str
    targetValue: str
    periodStart: str
    periodEnd: str
    approve: bool = False


@router.get("/dre")
async def departmental_dre(
    empresaCodigo: int = Query(...),
    data: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> dict:
    try:
        result = _service.build_dre(empresaCodigo, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Empresa fora do escopo licenciado") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Lote departamental não materializado")
    return {"success": True, "data": result, "error": None}


@router.get("/comparisons")
async def departmental_comparisons(
    data: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> dict:
    return {"success": True, "data": _comparison.build(data), "error": None}


@router.get("/trends")
async def departmental_trends(
    empresaCodigo: int = Query(...),
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> dict:
    try:
        data = _history.build(empresaCodigo, dataInicial, dataFinal)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"success": True, "data": data, "error": None}


@router.get("/presidency-cockpit")
async def presidency_cockpit(
    data: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> dict:
    return {"success": True, "data": _executive.cockpit(data), "error": None}


@router.get("/director-panels")
async def director_panels(
    empresaCodigo: int = Query(...),
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> dict:
    try:
        data = _executive.director_panels(empresaCodigo, dataInicial, dataFinal)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"success": True, "data": data, "error": None}


@router.get("/goals")
async def departmental_goals() -> dict:
    return {"success": True, "data": {"goals": _goals.list()}, "error": None}


@router.post("/goals")
async def save_departmental_goal(
    body: DepartmentalGoalBody,
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    try:
        payload = body.model_dump()
        if payload.pop("approve"):
            payload["approvedBy"] = str(current_user.get("sub") or "authenticated-user")
        data = _goals.save(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"success": True, "data": data, "error": None}
