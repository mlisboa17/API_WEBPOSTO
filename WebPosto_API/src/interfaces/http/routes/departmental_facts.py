"""Sprint 2 — materialização e qualidade dos fatos departamentais."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from src.interfaces.http.authz import require_roles

from src.gateway.webposto_client import WebPostoClient
from src.services.departmental_fact_pipeline import DepartmentalFactPipeline
from src.services.departmental_fact_store import DepartmentalFactStore

router = APIRouter(
    prefix="/api/v1/departmental-facts",
    tags=["Departmental Facts Sprint 2"],
)

_pipeline = DepartmentalFactPipeline(WebPostoClient())
_store = DepartmentalFactStore()


@router.post("/materialize")
async def materialize_departmental_facts(
    empresaCodigo: int = Query(...),
    data: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: dict = Depends(require_roles("operations", "director", "admin", "owner")),
) -> dict:
    result = await _pipeline.build_day(empresaCodigo, data)
    if result.get("blockingReasons") == ["UNLICENSED_COMPANY"]:
        raise HTTPException(status_code=422, detail="Empresa fora do escopo licenciado")
    if result.get("materialized"):
        _store.save(result)
    summary = (
        _store.quality_summary(empresaCodigo, data)
        if result.get("materialized")
        else {
            "companyCode": empresaCodigo,
            "day": data,
            "materialized": False,
            "publishable": False,
            "blockingReasons": result.get("blockingReasons") or [],
        }
    )
    return {"success": True, "data": summary, "error": None}


@router.get("/quality")
async def departmental_fact_quality(
    empresaCodigo: int = Query(...),
    data: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> dict:
    summary = _store.quality_summary(empresaCodigo, data)
    if summary is None:
        raise HTTPException(status_code=404, detail="Lote departamental não materializado")
    return {"success": True, "data": summary, "error": None}
