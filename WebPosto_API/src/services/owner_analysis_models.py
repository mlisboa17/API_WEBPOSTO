"""Contratos de freshness e refresh — PERFORMANCE-01."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.services.decision_discovery.models import TenantAnalysisRecord

TenantProgressCallback = Callable[
    ["TenantAnalysisRecord", int, int],
    Awaitable[None],
]


class FreshnessState(str, Enum):
    FRESH = "FRESH"
    STALE_REFRESHING = "STALE_REFRESHING"
    STALE = "STALE"
    NO_ANALYSIS = "NO_ANALYSIS"


class RefreshStatus(str, Enum):
    IDLE = "IDLE"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


DETECTOR_SET_SIGNATURE = "FuelRevenueDetector"
OWNER_ANALYSIS_FRESHNESS_TTL_SECONDS = 1800
OWNER_ANALYSIS_SNAPSHOT_DIR = "snapshots/owner_analysis"


@dataclass
class RefreshJob:
    analysis_id: str
    scope_key: str
    status: RefreshStatus
    started_at: str
    completed_at: str | None = None
    tenants_total: int = 0
    tenants_completed: int = 0
    tenants_failed: int = 0
    current_detector: str = DETECTOR_SET_SIGNATURE
    progress_message: str = ""
    error: str | None = None
    duplicate_prevented: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "scope_key": self.scope_key,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "tenants_total": self.tenants_total,
            "tenants_completed": self.tenants_completed,
            "tenants_failed": self.tenants_failed,
            "current_detector": self.current_detector,
            "progress_message": self.progress_message,
            "error": self.error,
            "duplicate_prevented": self.duplicate_prevented,
        }


@dataclass
class StoredAnalysisSnapshot:
    analysis_id: str
    response: dict[str, Any]
    period_start: str
    period_end: str
    scope_key: str
    created_at: str
    completed_at: str
    duration_ms: int
    expires_at: str
    refresh_status: RefreshStatus = RefreshStatus.COMPLETED
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_store_payload(self) -> dict[str, Any]:
        from src.utils.utc_datetime import utc_now_iso

        return {
            "lastUpdated": self.completed_at or utc_now_iso(),
            "snapshot": {
                "analysis_id": self.analysis_id,
                "response": self.response,
                "period_start": self.period_start,
                "period_end": self.period_end,
                "scope_key": self.scope_key,
                "created_at": self.created_at,
                "completed_at": self.completed_at,
                "duration_ms": self.duration_ms,
                "expires_at": self.expires_at,
                "refresh_status": self.refresh_status.value,
                "metrics": self.metrics,
            },
        }
