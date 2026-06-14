"""F08.2 — Configuração centralizada do scheduler/recovery financeiro."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from src.infrastructure.config.settings import settings
from src.services.financial_snapshot_service import SNAPSHOT_KINDS


@dataclass(frozen=True)
class FinancialSnapshotConfig:
    scheduler_enabled: bool
    refresh_interval_seconds: int
    retention_days: int
    rolling_days: int
    auto_recovery_enabled: bool
    recovery_interval_seconds: int
    snapshot_kinds: tuple[str, ...]

    @classmethod
    def from_settings(cls) -> FinancialSnapshotConfig:
        return cls(
            scheduler_enabled=settings.financial_scheduler_enabled,
            refresh_interval_seconds=settings.financial_snapshot_refresh_interval_seconds,
            retention_days=settings.financial_snapshot_retention_days,
            rolling_days=settings.financial_snapshot_rolling_days,
            auto_recovery_enabled=settings.financial_auto_recovery_enabled,
            recovery_interval_seconds=settings.financial_auto_recovery_interval_seconds,
            snapshot_kinds=SNAPSHOT_KINDS,
        )

    def default_period(self, *, reference: date | None = None) -> tuple[str, str]:
        end = reference or date.today()
        start = end - timedelta(days=max(1, self.rolling_days))
        return start.isoformat(), end.isoformat()

    def next_run_at(self, last_run: datetime | None) -> datetime | None:
        if not self.scheduler_enabled:
            return None
        base = last_run or datetime.now()
        return base + timedelta(seconds=self.refresh_interval_seconds)


def get_financial_snapshot_config() -> FinancialSnapshotConfig:
    return FinancialSnapshotConfig.from_settings()
