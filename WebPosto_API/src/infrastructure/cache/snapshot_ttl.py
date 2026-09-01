"""TTL unificado para snapshots executivos (Sprint 1)."""
from __future__ import annotations

from typing import Any

from src.services.snapshot_store import SnapshotStore

EXECUTIVE_SNAPSHOT_TTL_SECONDS = 300.0
FUEL_SNAPSHOT_TTL_SECONDS = 300.0


def build_snapshot_cache_meta(
    store: SnapshotStore,
    key: str,
    stored: dict[str, Any] | None,
    *,
    expired: bool,
) -> dict[str, Any]:
    """Metadados padronizados de cache-hit / stale para endpoints de snapshot."""
    if stored:
        return {
            "fromSnapshot": True,
            "cacheHit": not expired,
            "stale": expired,
            "ttlSeconds": store.ttl_seconds,
            "snapshotKey": key,
            "lastUpdated": stored.get("lastUpdated"),
        }
    return {
        "fromSnapshot": False,
        "cacheHit": False,
        "stale": True,
        "ttlSeconds": store.ttl_seconds,
        "snapshotKey": key,
        "lastUpdated": None,
    }
