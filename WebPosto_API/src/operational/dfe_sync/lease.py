"""Lease de sincronizacao. Impede duas execucoes simultaneas."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from src.operational.dfe import store

LEASE_SECONDS = 300


def _now() -> datetime:
    return datetime.now(timezone.utc)


def acquire_lease(company_code: int, *, environment: str = "PRODUCTION", ttl: int = LEASE_SECONDS) -> dict[str, Any]:
    state = store.get_sync_state(company_code, environment)
    expires = state.get("lease_expires_at")
    if expires:
        try:
            until = datetime.fromisoformat(expires)
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            if until > _now() and state.get("lease_owner"):
                return {"ok": False, "reason": "LEASE_HELD", "state": state}
        except ValueError:
            pass
    owner = f"dfe-sync-{uuid4().hex[:12]}"
    state["lease_owner"] = owner
    state["lease_expires_at"] = (_now() + timedelta(seconds=ttl)).isoformat()
    state["status"] = "RUNNING"
    store.save_sync_state(state)
    return {"ok": True, "owner": owner, "state": state}


def release_lease(company_code: int, owner: str, *, environment: str = "PRODUCTION") -> dict[str, Any]:
    state = store.get_sync_state(company_code, environment)
    if state.get("lease_owner") == owner:
        state["lease_owner"] = None
        state["lease_expires_at"] = None
        if state.get("status") == "RUNNING":
            state["status"] = "IDLE"
        store.save_sync_state(state)
    return state
