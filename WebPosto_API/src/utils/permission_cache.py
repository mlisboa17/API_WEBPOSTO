from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


_permission_entries: dict[str, dict[str, Any]] = {}


def _entry_key(credential_fingerprint: str) -> str:
    return credential_fingerprint or "_default"


def get_permissions(credential_fingerprint: str = "") -> dict[str, bool]:
    entry = _permission_entries.get(_entry_key(credential_fingerprint), {})
    perms = entry.get("permissions") or {}
    return dict(perms)


def set_permissions(perms: dict[str, bool], credential_fingerprint: str = "") -> None:
    key = _entry_key(credential_fingerprint)
    _permission_entries[key] = {
        "last_check": datetime.now(timezone.utc),
        "permissions": dict(perms),
    }


def is_cache_fresh(ttl_seconds: int, credential_fingerprint: str = "") -> bool:
    entry = _permission_entries.get(_entry_key(credential_fingerprint), {})
    last = entry.get("last_check")
    if not isinstance(last, datetime):
        return False
    return datetime.now(timezone.utc) - last < timedelta(seconds=ttl_seconds)


def clear_permissions(credential_fingerprint: str | None = None) -> None:
    if credential_fingerprint is None:
        _permission_entries.clear()
        return
    _permission_entries.pop(_entry_key(credential_fingerprint), None)
