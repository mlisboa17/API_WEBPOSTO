"""Lock entre processos para catch-up SDS. Sem segredos, sem rede."""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from src.services.sds_sanitize import sanitize_text, sanitize_value

LOCK_ID = 1
DEFAULT_LOCK_NAME = "sds_catchup_lock.sqlite"
DEFAULT_LOCK_DIRNAME = "WebPosto_API"


class LockUnavailable(RuntimeError):
    """Lock SDS não pôde ser criado ou aberto. Sem caminho de usuário."""


def sanitize_lock_path(path: str | Path) -> str:
    text = str(path)
    for key in ("LOCALAPPDATA", "USERPROFILE", "HOME", "APPDATA", "TEMP", "TMP"):
        value = (os.environ.get(key) or "").strip()
        if value:
            text = text.replace(value, f"%{key}%")
            text = text.replace(value.replace("\\", "/"), f"%{key}%")
    user = (os.environ.get("USERNAME") or os.environ.get("USER") or "").strip()
    if user and user.lower() not in {"system", "localappdata"}:
        text = text.replace(user, "%USER%")
    return sanitize_text(text)


class SdsProcessLock(Protocol):
    def acquire(self, trigger: str = "manual") -> bool: ...
    def release(self) -> bool: ...
    def peek(self) -> dict[str, Any] | None: ...


class NullSdsProcessLock:
    """No-op para testes unitários isolados do SQLite."""

    def acquire(self, trigger: str = "manual") -> bool:
        del trigger
        return True

    def release(self) -> bool:
        return True

    def peek(self) -> dict[str, Any] | None:
        return None


def process_start_key(pid: int) -> str | None:
    info = process_info(pid)
    return info[0]


def process_info(pid: int) -> tuple[str | None, bool]:
    """Retorna (start_key, em_execucao). PID morto nunca conta como vivo."""
    if pid <= 0:
        return None, False
    if os.name == "nt":
        return _windows_process_info(pid)
    key = _posix_start_key(pid)
    return key, key is not None


def owner_alive(pid: int, started: str) -> bool:
    current, running = process_info(pid)
    return bool(running and current and current == started)


def _posix_start_key(pid: int) -> str | None:
    try:
        return f"posix:{int(os.stat(f'/proc/{pid}').st_ctime_ns)}"
    except OSError:
        try:
            os.kill(pid, 0)
        except OSError:
            return None
        return f"posix-alive:{pid}"


def _windows_process_info(pid: int) -> tuple[str | None, bool]:
    import ctypes
    from ctypes import wintypes

    process_query_limited = 0x1000
    still_active = 259

    class FileTime(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenProcess(process_query_limited, False, int(pid))
    if not handle:
        return None, False
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return None, False
        running = int(exit_code.value) == still_active
        created = FileTime()
        exited = FileTime()
        kernel = FileTime()
        user = FileTime()
        ok = kernel32.GetProcessTimes(
            handle,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel),
            ctypes.byref(user),
        )
        if not ok:
            return None, running
        ticks = (int(created.dwHighDateTime) << 32) | int(created.dwLowDateTime)
        return f"win:{ticks}", running
    finally:
        kernel32.CloseHandle(handle)


def default_lock_path() -> Path:
    override = os.environ.get("SDS_CATCHUP_LOCK_PATH", "").strip()
    if override:
        return Path(override)
    local = (os.environ.get("LOCALAPPDATA") or "").strip()
    if not local:
        raise LockUnavailable("LOCALAPPDATA indisponivel para o lock SDS")
    return Path(local) / DEFAULT_LOCK_DIRNAME / DEFAULT_LOCK_NAME


class SqliteSdsProcessLock:
    """Aquisição atômica via BEGIN IMMEDIATE em SQLite local."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_lock_path()
        self._token: str | None = None
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(self.path.as_posix(), timeout=5, isolation_level=None)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA busy_timeout=5000")
            return con
        except LockUnavailable:
            raise
        except Exception:
            raise LockUnavailable("nao foi possivel abrir o lock SDS") from None

    def _ensure_schema(self) -> None:
        try:
            con = self._connect()
            try:
                con.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sds_catchup_lock (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        owner_token TEXT NOT NULL,
                        owner_pid INTEGER NOT NULL,
                        owner_started_at TEXT NOT NULL,
                        acquired_at TEXT NOT NULL,
                        trigger_name TEXT NOT NULL
                    )
                    """
                )
            finally:
                con.close()
        except LockUnavailable:
            raise
        except Exception:
            raise LockUnavailable("nao foi possivel preparar o lock SDS") from None

    def acquire(self, trigger: str = "manual") -> bool:
        pid = os.getpid()
        started = process_start_key(pid)
        if not started:
            return False
        token = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        trigger_name = sanitize_text(str(trigger or "manual"))[:80]
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT owner_token, owner_pid, owner_started_at, acquired_at, trigger_name "
                "FROM sds_catchup_lock WHERE id=?",
                (LOCK_ID,),
            ).fetchone()
            if row is not None and owner_alive(int(row["owner_pid"]), str(row["owner_started_at"])):
                con.execute("ROLLBACK")
                return False
            con.execute("DELETE FROM sds_catchup_lock WHERE id=?", (LOCK_ID,))
            con.execute(
                """
                INSERT INTO sds_catchup_lock
                    (id, owner_token, owner_pid, owner_started_at, acquired_at, trigger_name)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (LOCK_ID, token, pid, started, now, trigger_name),
            )
            con.execute("COMMIT")
            self._token = token
            return True
        except LockUnavailable:
            raise
        except Exception:
            try:
                con.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise LockUnavailable("nao foi possivel adquirir o lock SDS") from None
        finally:
            con.close()

    def release(self) -> bool:
        if not self._token:
            return False
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT owner_token FROM sds_catchup_lock WHERE id=?",
                (LOCK_ID,),
            ).fetchone()
            if row is None or str(row["owner_token"]) != self._token:
                con.execute("ROLLBACK")
                return False
            con.execute("DELETE FROM sds_catchup_lock WHERE id=?", (LOCK_ID,))
            con.execute("COMMIT")
            self._token = None
            return True
        except LockUnavailable:
            raise
        except Exception:
            try:
                con.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise LockUnavailable("nao foi possivel liberar o lock SDS") from None
        finally:
            con.close()

    def peek(self) -> dict[str, Any] | None:
        con = self._connect()
        try:
            row = con.execute(
                "SELECT owner_pid, owner_started_at, acquired_at, trigger_name "
                "FROM sds_catchup_lock WHERE id=?",
                (LOCK_ID,),
            ).fetchone()
        finally:
            con.close()
        if row is None:
            return None
        return sanitize_value(
            {
                "status": "LOCKED",
                "ownerPid": int(row["owner_pid"]),
                "ownerAlive": owner_alive(int(row["owner_pid"]), str(row["owner_started_at"])),
                "acquiredAt": str(row["acquired_at"]),
                "trigger": str(row["trigger_name"]),
            }
        )

    def mark_acquired_at_for_test(self, acquired_at: str) -> None:
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "UPDATE sds_catchup_lock SET acquired_at=? WHERE id=?",
                (acquired_at, LOCK_ID),
            )
            con.execute("COMMIT")
        finally:
            con.close()


def production_process_lock() -> SqliteSdsProcessLock:
    try:
        return SqliteSdsProcessLock(default_lock_path())
    except LockUnavailable:
        raise
    except Exception:
        raise LockUnavailable("nao foi possivel iniciar o lock SDS") from None
