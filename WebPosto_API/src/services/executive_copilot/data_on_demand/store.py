"""SQLite dedicado do DATA-ON-DEMAND. BEGIN IMMEDIATE; sem OneDrive; sem SDS."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.services.executive_copilot.data_on_demand.states import ACTIVE_STATES, DataRequestState
from src.services.sds_process_lock import sanitize_lock_path
from src.services.sds_sanitize import sanitize_text, sanitize_value

_SCHEMA = """
CREATE TABLE IF NOT EXISTS data_requests (
    request_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL,
    state TEXT NOT NULL,
    plan_hash TEXT NOT NULL,
    operation TEXT NOT NULL,
    logical_endpoint TEXT NOT NULL,
    units_json TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    gaps_json TEXT NOT NULL,
    authorized_scope_json TEXT NOT NULL,
    progress_json TEXT NOT NULL,
    estimated_seconds_min INTEGER NOT NULL,
    estimated_seconds_max INTEGER NOT NULL,
    queue_delay_seconds INTEGER NOT NULL,
    estimate_confidence TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    expires_at TEXT,
    confirmed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_dod_idempotency ON data_requests(idempotency_key, state);
CREATE TABLE IF NOT EXISTS data_request_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    at TEXT NOT NULL,
    event TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT,
    detail TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS data_request_pair_locks (
    unit INTEGER NOT NULL,
    day TEXT NOT NULL,
    request_id TEXT NOT NULL,
    PRIMARY KEY (unit, day)
);
"""


def default_store_path() -> Path:
    override = (os.environ.get("DATA_ON_DEMAND_DB_PATH") or "").strip()
    if override:
        return Path(override)
    local = (os.environ.get("LOCALAPPDATA") or "").strip()
    if not local:
        raise RuntimeError("LOCALAPPDATA indisponivel para o store DATA-ON-DEMAND")
    return Path(local) / "WebPosto_API" / "data_on_demand.sqlite"


class DataRequestStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def sanitized_path(self) -> str:
        return sanitize_lock_path(self.path)

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path.as_posix(), timeout=5, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA busy_timeout=5000")
        return con

    def _ensure_schema(self) -> None:
        con = self._connect()
        try:
            con.executescript(_SCHEMA)
        finally:
            con.close()

    def insert_plan(self, row: dict[str, Any], event_detail: dict[str, Any]) -> dict[str, Any] | None:
        """Insere plano ou devolve o ativo duplicado. Não persiste 6666."""
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            existing = con.execute(
                "SELECT * FROM data_requests WHERE idempotency_key=? AND state IN ({}) "
                "ORDER BY created_at LIMIT 1".format(
                    ",".join("?" for _ in ACTIVE_STATES)
                ),
                [row["idempotency_key"], *[item.value for item in ACTIVE_STATES]],
            ).fetchone()
            if existing is not None:
                con.execute("COMMIT")
                return _row_to_dict(existing)
            con.execute(
                """
                INSERT INTO data_requests (
                    request_id, idempotency_key, state, plan_hash, operation, logical_endpoint,
                    units_json, start_date, end_date, gaps_json, authorized_scope_json,
                    progress_json, estimated_seconds_min, estimated_seconds_max,
                    queue_delay_seconds, estimate_confidence, created_by, created_at,
                    updated_at, expires_at, confirmed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["request_id"],
                    row["idempotency_key"],
                    row["state"],
                    row["plan_hash"],
                    row["operation"],
                    row["logical_endpoint"],
                    json.dumps(row["units"]),
                    row["start_date"],
                    row["end_date"],
                    json.dumps(row["gaps"]),
                    json.dumps(row["authorized_scope"]),
                    json.dumps(row["progress"]),
                    row["estimated_seconds_min"],
                    row["estimated_seconds_max"],
                    row["queue_delay_seconds"],
                    row["estimate_confidence"],
                    row["created_by"],
                    row["created_at"],
                    row["updated_at"],
                    row["expires_at"],
                    None,
                ),
            )
            _append_event(con, row["request_id"], "PLANNED", None, row["state"], event_detail)
            con.execute("COMMIT")
            return None
        except Exception:
            con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    def get(self, request_id: str) -> dict[str, Any] | None:
        con = self._connect()
        try:
            row = con.execute("SELECT * FROM data_requests WHERE request_id=?", (request_id,)).fetchone()
        finally:
            con.close()
        return _row_to_dict(row) if row else None

    def transition(
        self,
        request_id: str,
        expected: DataRequestState | frozenset[DataRequestState],
        new_state: DataRequestState,
        *,
        extra: dict[str, Any] | None = None,
        event: str,
        detail: dict[str, Any],
    ) -> dict[str, Any] | None:
        expected_states = {expected} if isinstance(expected, DataRequestState) else set(expected)
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM data_requests WHERE request_id=?", (request_id,)).fetchone()
            if row is None or DataRequestState(row["state"]) not in expected_states:
                con.execute("ROLLBACK")
                return None
            now = (extra or {}).get("updated_at") or datetime.now(timezone.utc).isoformat()
            assignments = ["state=?", "updated_at=?"]
            values: list[Any] = [new_state.value, now]
            if extra:
                if "progress" in extra:
                    assignments.append("progress_json=?")
                    values.append(json.dumps(extra["progress"]))
                if "confirmed_at" in extra:
                    assignments.append("confirmed_at=?")
                    values.append(extra["confirmed_at"])
            values.append(request_id)
            con.execute(
                f"UPDATE data_requests SET {', '.join(assignments)} WHERE request_id=?",
                values,
            )
            _append_event(con, request_id, event, row["state"], new_state.value, detail)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        finally:
            con.close()
        return self.get(request_id)

    def acquire_pairs(self, request_id: str, pairs: list[tuple[int, str]]) -> bool:
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            for unit, day in pairs:
                held = con.execute(
                    "SELECT request_id FROM data_request_pair_locks WHERE unit=? AND day=?",
                    (unit, day),
                ).fetchone()
                if held is not None and str(held["request_id"]) != request_id:
                    con.execute("ROLLBACK")
                    return False
                con.execute(
                    "INSERT OR IGNORE INTO data_request_pair_locks (unit, day, request_id) VALUES (?, ?, ?)",
                    (unit, day, request_id),
                )
            con.execute("COMMIT")
            return True
        except Exception:
            con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    def release_own_pairs(self, request_id: str) -> None:
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute("DELETE FROM data_request_pair_locks WHERE request_id=?", (request_id,))
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    def events(self, request_id: str) -> list[dict[str, Any]]:
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT at, event, from_state, to_state, detail FROM data_request_events "
                "WHERE request_id=? ORDER BY id",
                (request_id,),
            ).fetchall()
        finally:
            con.close()
        return [
            sanitize_value(
                {
                    "at": row["at"],
                    "event": row["event"],
                    "fromState": row["from_state"],
                    "toState": row["to_state"],
                    "detail": json.loads(row["detail"]),
                }
            )
            for row in rows
        ]

    def raw_blob(self) -> str:
        con = self._connect()
        try:
            rows = con.execute("SELECT * FROM data_requests").fetchall()
            events = con.execute("SELECT detail FROM data_request_events").fetchall()
        finally:
            con.close()
        return json.dumps([dict(row) for row in rows] + [dict(row) for row in events])


def _append_event(
    con: sqlite3.Connection,
    request_id: str,
    event: str,
    from_state: str | None,
    to_state: str | None,
    detail: dict[str, Any],
) -> None:
    con.execute(
        "INSERT INTO data_request_events (request_id, at, event, from_state, to_state, detail) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            request_id,
            datetime.now(timezone.utc).isoformat(),
            sanitize_text(event),
            from_state,
            to_state,
            json.dumps(sanitize_value(detail)),
        ),
    )


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "request_id": row["request_id"],
        "idempotency_key": row["idempotency_key"],
        "state": DataRequestState(row["state"]),
        "plan_hash": row["plan_hash"],
        "operation": row["operation"],
        "logical_endpoint": row["logical_endpoint"],
        "units": json.loads(row["units_json"]),
        "start_date": row["start_date"],
        "end_date": row["end_date"],
        "gaps": json.loads(row["gaps_json"]),
        "authorized_scope": json.loads(row["authorized_scope_json"]),
        "progress": json.loads(row["progress_json"]),
        "estimated_seconds_min": row["estimated_seconds_min"],
        "estimated_seconds_max": row["estimated_seconds_max"],
        "queue_delay_seconds": row["queue_delay_seconds"],
        "estimate_confidence": row["estimate_confidence"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "expires_at": row["expires_at"],
        "confirmed_at": row["confirmed_at"],
    }
