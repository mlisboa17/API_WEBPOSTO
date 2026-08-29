"""Endpoints operacionais do SDS (status read-only + run-now já existente)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.interfaces.http.authz import require_roles
from src.services.data_sync_scheduler import CRON_EXPR, get_data_sync_scheduler
from src.services.sds_catchup_service import get_sds_catchup_service
from src.services.sds_sanitize import sanitize_value
from src.services.webposto.schemas import WEBPOSTO_WRITES
from src.services.webposto.write_policy import is_webposto_write_path

router = APIRouter(prefix="/api/v1/ops/data-sync", tags=["Data Sync Hybrid"])
_ROLES = ("director", "admin", "owner", "audit")


@router.get("/status")
async def data_sync_status(
    current_user: dict = Depends(require_roles(*_ROLES)),
) -> dict:
    sched = get_data_sync_scheduler().get_status()
    snap = await get_sds_catchup_service().operational_snapshot()
    last = snap.get("ultimoResultado") or {}
    counters = last.get("contadores") or {}
    return sanitize_value(
        {
            "success": True,
            "webpostoWrites": WEBPOSTO_WRITES,
            "usuarioPerfil": current_user.get("role"),
            "data": {
                "cron": CRON_EXPR,
                "proximaExecucao": sched.get("next_run_at"),
                "ultimaExecucao": snap.get("ultimaExecucao") or sched.get("last_run_at"),
                "ultimaDataConsolidada": snap.get("ultimaDataConsolidada"),
                "diasPendentes": snap.get("diasPendentesEstimados"),
                "execucaoEmAndamento": bool(snap.get("execucaoEmAndamento") or sched.get("job_running")),
                "ultimoResultado": {
                    "success": last.get("success"),
                    "trigger": last.get("trigger"),
                    "intervalo": last.get("intervalo"),
                    "contadores": counters,
                    "mensagem": last.get("mensagem"),
                },
                "sucessos": counters.get("SUCESSO", 0),
                "parciais": counters.get("PARCIAL", 0),
                "falhas": counters.get("FALHA", 0),
                "scheduler": sched,
                "writePath": is_webposto_write_path("/api/v1/ops/data-sync/status"),
            },
        }
    )


@router.post("/run-now")
async def data_sync_run_now(
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    result = await get_data_sync_scheduler().run_now()
    return sanitize_value({"success": bool(result.get("success")), "data": result, "webpostoWrites": WEBPOSTO_WRITES})
