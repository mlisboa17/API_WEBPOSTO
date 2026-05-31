import os
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter
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


@router.get("/health")
async def health_check():
    """Health check endpoint verifies DB connectivity."""
    database_url = os.getenv("DATABASE_URL", settings.database_url)
    is_sqlite = "sqlite" in (database_url or "").lower()

    if is_sqlite:
        db_path = _sqlite_db_path(database_url)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            can_write, writable_target = _cached_sqlite_write_probe(db_path)
            if not can_write:
                raise RuntimeError("SQLite storage is not writable")
            return {
                "status": "healthy",
                "service": "webposto-service",
                "db": "ok",
                "database": "sqlite",
                "writable": writable_target,
            }
        except Exception as exc:
            return {
                "status": "unhealthy",
                "service": "webposto-service",
                "db": "down",
                "database": "sqlite",
                "detail": str(exc)[:200],
            }

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        return {
            "status": "unhealthy",
            "service": "webposto-service",
            "db": "down",
            "database": "primary",
            "detail": str(exc)[:200],
        }
    return {
        "status": "healthy",
        "service": "webposto-service",
        "db": "ok",
        "database": "primary",
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {"ready": True, "service": "webposto-service"}
