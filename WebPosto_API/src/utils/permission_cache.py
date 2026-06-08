from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

permission_cache: dict[str, Any] = {
    "last_check": None,
    "permissions": {},
}


def get_permissions() -> dict[str, bool]:
    perms = permission_cache.get("permissions") or {}
    return dict(perms)


def set_permissions(perms: dict[str, bool]) -> None:
    permission_cache["last_check"] = datetime.now(timezone.utc)
    permission_cache["permissions"] = dict(perms)


def is_cache_fresh(ttl_seconds: int) -> bool:
    last = permission_cache.get("last_check")
    if not isinstance(last, datetime):
        return False
    return datetime.now(timezone.utc) - last < timedelta(seconds=ttl_seconds)
