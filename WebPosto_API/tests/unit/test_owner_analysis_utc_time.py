from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.services.owner_analysis_models import (
    OWNER_ANALYSIS_FRESHNESS_TTL_SECONDS,
    FreshnessState,
    StoredAnalysisSnapshot,
    RefreshStatus,
)
from src.services.owner_analysis_snapshot_service import OwnerAnalysisSnapshotService
from src.services.snapshot_store import SnapshotStore
from src.utils.utc_datetime import age_seconds, parse_utc_datetime, utc_now, utc_now_iso


def test_a_iso_aware_and_now_aware() -> None:
    aware = "2026-07-04T00:00:00+00:00"
    parsed = parse_utc_datetime(aware)
    now = utc_now()
    assert parsed.tzinfo is not None
    assert now.tzinfo is not None
    assert age_seconds(aware, now=now) >= 0


def test_b_legacy_naive_snapshot_treated_as_utc() -> None:
    naive = "2026-07-04T00:00:00"
    now = datetime(2026, 7, 4, 0, 5, 0, tzinfo=timezone.utc)
    assert age_seconds(naive, now=now) == 300


def test_c_expires_at_aware() -> None:
    future = (utc_now() + timedelta(minutes=10)).isoformat()
    past = (utc_now() - timedelta(minutes=10)).isoformat()
    assert utc_now() <= parse_utc_datetime(future)
    assert utc_now() > parse_utc_datetime(past)


def test_d_created_at_aware() -> None:
    created = utc_now_iso()
    assert parse_utc_datetime(created).tzinfo == timezone.utc


def test_e_age_seconds_non_negative() -> None:
    assert age_seconds(utc_now_iso()) == 0


def test_f_ttl_expiration_and_freshness() -> None:
    store = SnapshotStore("snapshots/test_ttl", ttl_seconds=60)
    fresh_payload = {"lastUpdated": utc_now_iso(), "snapshot": {}}
    stale_payload = {
        "lastUpdated": (utc_now() - timedelta(minutes=5)).replace(tzinfo=timezone.utc).isoformat(),
        "snapshot": {},
    }
    assert store.is_expired(fresh_payload) is False
    assert store.is_expired(stale_payload) is True

    svc = OwnerAnalysisSnapshotService(freshness_ttl_seconds=60)
    stored = StoredAnalysisSnapshot(
        analysis_id="id",
        response={"success": True},
        period_start="2026-06-26",
        period_end="2026-07-03",
        scope_key="scope",
        created_at=utc_now_iso(),
        completed_at=utc_now_iso(),
        duration_ms=1,
        expires_at=(utc_now() + timedelta(seconds=60)).isoformat(),
        refresh_status=RefreshStatus.COMPLETED,
    )
    assert svc._is_snapshot_fresh(stored) is True
    stored_stale = StoredAnalysisSnapshot(
        analysis_id="id",
        response={"success": True},
        period_start="2026-06-26",
        period_end="2026-07-03",
        scope_key="scope",
        created_at=(utc_now() - timedelta(hours=2)).isoformat(),
        completed_at=(utc_now() - timedelta(hours=2)).isoformat(),
        duration_ms=1,
        expires_at=(utc_now() - timedelta(hours=1)).isoformat(),
        refresh_status=RefreshStatus.COMPLETED,
    )
    assert svc._is_snapshot_fresh(stored_stale) is False
    assert svc._resolve_freshness(stored_stale, "scope") == FreshnessState.STALE
