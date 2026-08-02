from __future__ import annotations
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query

from src.interfaces.http.authz import require_roles
from src.services.employee_performance_service import EmployeePerformanceService
from src.interfaces.http.schemas.executive_employee_schema import EmployeePerformanceSummary

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive/employees",
    tags=["Executive Employees S55"],
)

_service = EmployeePerformanceService()


@router.get("/performance", response_model=dict)
async def get_employee_performance(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: Optional[int] = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
):
    """
    Retorna ranking de frentistas, produtividade e auditoria de caixa por operador.
    """
    try:
        data = await _service.analyze(dataInicial, dataFinal, empresaCodigo)
        return {"success": True, "data": data, "namespace": "executive"}
    except Exception as e:
        logger.error(f"Erro em employee performance: {str(e)}")
        return {"success": False, "error": str(e)}
