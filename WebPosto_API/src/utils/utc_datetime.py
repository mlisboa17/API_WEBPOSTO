"""Contrato UTC timezone-aware — Fast Daily Analysis Loop / SnapshotStore."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso(*, timespec: str = "seconds") -> str:
    return utc_now().isoformat(timespec=timespec)


def parse_utc_datetime(value: str | datetime) -> datetime:
    """Normaliza ISO persistido para UTC aware. Snapshots legados naive = UTC."""
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def age_seconds(value: str | datetime, *, now: datetime | None = None) -> int:
    reference = now or utc_now()
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    delta = reference - parse_utc_datetime(value)
    return max(0, int(delta.total_seconds()))


def is_past_ttl(value: str | datetime, ttl_seconds: float, *, now: datetime | None = None) -> bool:
    return age_seconds(value, now=now) > ttl_seconds
