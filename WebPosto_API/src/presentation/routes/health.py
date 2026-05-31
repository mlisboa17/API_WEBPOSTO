from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import text

from src.infrastructure.config.database import engine
from src.infrastructure.config.settings import settings

router = APIRouter(tags=["health"])
_WRITE_PROBE_CACHE: dict[str, object] = {"ts": 0.0, "ok": False, "target": ""}


def _sqlite_db_path(database_url: str) -> Path:
    raw = database_url.replace("sqlite+aiosqlite:///", "", 1)
    path = Path(raw)
    return path if path.is_absolute() else (Path.cwd() / path)


def _probe_write(target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    marker = target.parent / ".health_probe"
    marker.write_text("ok", encoding="utf-8")
    marker.unlink(missing_ok=True)
    return str(target.parent)


def _cached_probe(db_path: Path) -> tuple[bool, str]:
    now = time.monotonic()
    last = float(_WRITE_PROBE_CACHE.get("ts", 0.0))
    if now - last < 30:
        return bool(_WRITE_PROBE_CACHE.get("ok", False)), str(
            _WRITE_PROBE_CACHE.get("target", "")
        )

    try:
        writable = _probe_write(db_path)
        ok, target = True, writable
    except Exception:
        try:
            writable = _probe_write(Path(tempfile.gettempdir()) / "webposto.db")
            ok, target = True, writable
        except Exception:
            ok, target = False, ""

    _WRITE_PROBE_CACHE["ts"] = now
    _WRITE_PROBE_CACHE["ok"] = ok
    _WRITE_PROBE_CACHE["target"] = target
    return ok, target


@router.get("/ready")
async def ready() -> dict[str, str]:
    return {"status": "ready"}


@router.get("/health")
async def health() -> dict[str, str]:
    database_url = os.getenv("DATABASE_URL", settings.database_url)

    if "sqlite" in (database_url or "").lower():
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_path = _sqlite_db_path(database_url)
            ok, writable = _cached_probe(db_path)
            if not ok:
                raise RuntimeError("SQLite storage is not writable")
            return {"status": "healthy", "database": "up", "type": "local_sqlite", "writable": writable}
        except Exception as exc:
            return {"status": "unhealthy", "database": "down", "type": "local_sqlite", "error": str(exc)[:200]}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "up", "type": "remote"}
    except Exception as exc:
        return {"status": "unhealthy", "database": "down", "type": "remote", "error": str(exc)[:200]}
