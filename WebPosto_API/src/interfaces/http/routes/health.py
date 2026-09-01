"""Health / readiness — sempre HTTP 200 com status detalhado dos subsistemas."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import text

from src.infrastructure.config.database import engine
from src.infrastructure.config.settings import settings

router = APIRouter(tags=["Health"])
_WRITE_PROBE_CACHE: dict[str, object] = {"ts": 0.0, "ok": False, "target": ""}


def _sqlite_db_path(database_url: str) -> Path:
    raw = database_url.replace("sqlite+aiosqlite:///", "", 1)
    p = Path(raw)
    return p if p.is_absolute() else (Path.cwd() / p)


def _can_write(path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    marker = path.parent / ".health_write_check"
    marker.write_text("ok", encoding="utf-8")
    marker.unlink(missing_ok=True)
    return True


def _cached_sqlite_write_probe(db_path: Path) -> tuple[bool, str]:
    now = time.monotonic()
    last = float(_WRITE_PROBE_CACHE.get("ts", 0.0))
    if now - last < 30:
        return bool(_WRITE_PROBE_CACHE.get("ok", False)), str(
            _WRITE_PROBE_CACHE.get("target", "")
        )

    try:
        _can_write(db_path)
        ok, target = True, str(db_path)
    except Exception:
        try:
            tmp_probe = Path(tempfile.gettempdir()) / "webposto_health.tmp"
            _can_write(tmp_probe)
            ok, target = True, str(tmp_probe.parent)
        except Exception:
            ok, target = False, ""

    _WRITE_PROBE_CACHE["ts"] = now
    _WRITE_PROBE_CACHE["ok"] = ok
    _WRITE_PROBE_CACHE["target"] = target
    return ok, target


async def _probe_database() -> dict[str, Any]:
    database_url = os.getenv("DATABASE_URL", settings.database_url)
    is_sqlite = "sqlite" in (database_url or "").lower()
    kind = "sqlite" if is_sqlite else "primary"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        detail: dict[str, Any] = {"status": "ok", "engine": kind}
        if is_sqlite:
            db_path = _sqlite_db_path(database_url)
            can_write, writable_target = _cached_sqlite_write_probe(db_path)
            detail["writable"] = can_write
            detail["writable_target"] = writable_target or None
            if not can_write:
                detail["status"] = "degraded"
                detail["detail"] = "SQLite storage not writable"
        return detail
    except Exception as exc:
        return {
            "status": "down",
            "engine": kind,
            "detail": str(exc)[:200],
        }


def _probe_webposto_client() -> dict[str, Any]:
    """Não chama a API remota — apenas presença de configuração (sem vazar chaves)."""
    keys = [
        settings.webposto_api_key,
        settings.webposto_token,
        settings.webposto_app_key,
        settings.webposto_casa_caiada_key,
        settings.webposto_vip_key,
        settings.webposto_real_doze_key,
        settings.webposto_api_key_posto_casa_caiada,
        settings.webposto_api_key_posto_vip_rio_doce,
        settings.webposto_api_key_posto_doze_filial_ii,
    ]
    configured = sum(1 for k in keys if (k or "").strip())
    base = (settings.webposto_base_url or settings.webposto_api_url or "").strip()
    if configured > 0 and base:
        return {
            "status": "configured",
            "base_url_set": True,
            "keys_configured": configured,
        }
    if configured > 0 or base:
        return {
            "status": "partial",
            "base_url_set": bool(base),
            "keys_configured": configured,
        }
    return {
        "status": "unconfigured",
        "base_url_set": False,
        "keys_configured": 0,
    }


def _probe_pista_cache() -> dict[str, Any]:
    try:
        from src.services.pista_cache_service import get_pista_cache

        cache = get_pista_cache()
        snap = cache.get_snapshot()
        return {
            "status": "ok",
            "ultima_sincronizacao_iso": getattr(snap, "ultima_sincronizacao_iso", None),
            "last_error": getattr(snap, "last_error", None) or None,
            "last_duration_ms": getattr(snap, "last_duration_ms", None),
            "total_baixados": len(getattr(snap, "baixados", None) or []),
            "total_pendentes": len(getattr(snap, "pendentes", None) or []),
        }
    except Exception as exc:
        return {"status": "unavailable", "detail": str(exc)[:200]}


def _probe_workers(request: Request) -> dict[str, Any]:
    from src.services.webposto.offline_mode import webposto_offline_mode

    offline = webposto_offline_mode()
    workers: dict[str, Any] = {
        "pista_sync_configured": bool(settings.pista_sync_worker_enabled) and not offline,
        "data_sync_configured": bool(settings.data_sync_scheduler_enabled) and not offline,
        "api_workers": int(settings.api_workers or 1),
        "operational_routes_enabled": bool(
            getattr(settings, "enable_operational_routes", True)
        ),
        "offline_suppressed": offline,
    }
    pista = getattr(request.app.state, "pista_sync_worker", None)
    if pista is not None and hasattr(pista, "get_status"):
        st = pista.get_status()
        workers["pista_sync"] = {
            "status": "running" if st.get("loop_running") else "stopped",
            **st,
        }
    elif offline:
        workers["pista_sync"] = {"status": "disabled", "reason": "offline_mode"}
    elif settings.pista_sync_worker_enabled:
        workers["pista_sync"] = {"status": "pending_or_unavailable"}
    else:
        workers["pista_sync"] = {"status": "disabled"}

    data_sync = getattr(request.app.state, "data_sync_scheduler", None)
    if data_sync is not None:
        sched = data_sync.get_status() if hasattr(data_sync, "get_status") else {}
        workers["data_sync"] = {
            "status": "scheduled",
            "enabled": True,
            "job_running": bool(sched.get("job_running")),
            "next_run_at": sched.get("next_run_at"),
        }
    elif offline:
        workers["data_sync"] = {"status": "disabled", "reason": "offline_mode"}
    elif settings.data_sync_scheduler_enabled:
        workers["data_sync"] = {"status": "pending_or_unavailable"}
    else:
        workers["data_sync"] = {"status": "disabled"}

    return workers


def _aggregate_status(subsystems: dict[str, Any]) -> str:
    db = (subsystems.get("database") or {}).get("status")
    if db == "down":
        # Processo no ar; DB indisponível = degradado (não derruba load balancer)
        return "degraded"
    statuses = []
    for key, val in subsystems.items():
        if isinstance(val, dict) and "status" in val:
            statuses.append(str(val["status"]))
        elif key == "workers" and isinstance(val, dict):
            ps = (val.get("pista_sync") or {}).get("status")
            if ps:
                statuses.append(str(ps))
    if any(s in {"down", "unconfigured"} for s in statuses):
        return "degraded"
    if any(s in {"degraded", "partial", "pending_or_unavailable"} for s in statuses):
        return "degraded"
    return "healthy"


@router.get("/health")
async def health_check(request: Request):
    """
    Liveness + diagnóstico de subsistemas.

    Sempre retorna HTTP 200 com payload detalhado (DB, cache RAM, WebPosto, workers).
    Falhas momentâneas de DB/API não derrubam o status HTTP.
    """
    subsystems: dict[str, Any] = {
        "database": await _probe_database(),
        "cache_ram": _probe_pista_cache(),
        "webposto_client": _probe_webposto_client(),
        "workers": _probe_workers(request),
    }
    from src.services.webposto.offline_mode import webposto_offline_mode

    offline = webposto_offline_mode()
    if offline:
        subsystems["webposto_client"] = {
            **(subsystems.get("webposto_client") or {}),
            "status": "offline",
            "network": "blocked",
        }
    overall = _aggregate_status(subsystems)
    return {
        "status": overall,
        "service": "webposto-service",
        "version": settings.api_version,
        "environment": settings.environment,
        "offlineMode": offline,
        "subsystems": subsystems,
        # Compat legada (auditores / FE antigos)
        "db": subsystems["database"].get("status", "unknown"),
        "database": subsystems["database"].get("engine", "primary"),
    }


@router.get("/ready")
async def readiness_check(request: Request):
    """Readiness com o mesmo diagnóstico — sempre HTTP 200."""
    body = await health_check(request)
    return {
        "ready": body.get("status") in {"healthy", "degraded"},
        "service": "webposto-service",
        "status": body.get("status"),
        "offlineMode": bool(body.get("offlineMode")),
        "subsystems": body.get("subsystems"),
    }
