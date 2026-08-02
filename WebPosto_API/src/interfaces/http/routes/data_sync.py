"""Endpoints operacionais do sync híbrido (status / run-now)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.interfaces.http.authz import require_roles
from src.services.data_sync_scheduler import CRON_EXPR, get_data_sync_scheduler
from src.services.data_sync_service import get_data_sync_service

router = APIRouter(prefix="/api/v1/ops/data-sync", tags=["Data Sync Hybrid"])


@router.get("/status")
async def data_sync_status(
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    sched = get_data_sync_scheduler().get_status()
    products = await get_data_sync_service().list_discovered_products()
    return {
        "success": True,
        "data": {
            "cron": CRON_EXPR,
            "scheduler": sched,
            "produtos_mapeados": len(products),
            "produtos": products,
        },
    }


@router.post("/run-now")
async def data_sync_run_now(
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    result = await get_data_sync_scheduler().run_now()
    return {"success": bool(result.get("success")), "data": result}
