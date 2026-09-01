"""Cobertura SDS por checkpoint local. Sem MAX(data) e sem rede."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol

from src.services.executive_copilot.contracts import WEBPOSTO_WRITES
from src.services.sds_identity import COMPLETE_STATUSES, LICENSED_SDS_CODES


@dataclass(frozen=True)
class DayCheckpoint:
    empresa_codigo: int
    data_referencia: date
    status: str
    quantidade_abastecimentos: int | None = None
    registros_sem_identidade: int = 0


class CheckpointStore(Protocol):
    def list_days(self, units: list[int], start: date, end: date) -> list[DayCheckpoint]: ...
    def list_available(self, units: list[int]) -> list[DayCheckpoint]: ...


class MemoryCheckpointStore:
    def __init__(self, rows: list[DayCheckpoint] | None = None) -> None:
        self._rows = list(rows or [])

    def list_days(self, units: list[int], start: date, end: date) -> list[DayCheckpoint]:
        allowed = set(units)
        return [
            row
            for row in self._rows
            if row.empresa_codigo in allowed and start <= row.data_referencia <= end
        ]

    def list_available(self, units: list[int]) -> list[DayCheckpoint]:
        allowed = set(units)
        return [row for row in self._rows if row.empresa_codigo in allowed]


def _daterange(start: date, end: date) -> list[date]:
    days: list[date] = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


class CheckpointSdsCoverageProvider:
    """Completude = todos os dias do período, em todas as unidades, com status completo."""

    def __init__(
        self,
        store: CheckpointStore,
        units: list[int],
        start: date,
        end: date,
    ) -> None:
        self._units = [code for code in units if code in LICENSED_SDS_CODES]
        self._start = start
        self._end = end
        self.gaps: list[dict[str, object]] = []
        self._last_complete = self._compute(store)

    def last_complete_date(self) -> date | None:
        return self._last_complete

    def period_complete(self) -> bool:
        return self._last_complete == self._end and not self.gaps

    def _compute(self, store: CheckpointStore) -> date | None:
        if not self._units or self._start > self._end:
            return None
        by_key = {
            (row.empresa_codigo, row.data_referencia): row
            for row in store.list_days(self._units, self._start, self._end)
        }
        last_ok: date | None = None
        for day in _daterange(self._start, self._end):
            missing: list[int] = []
            for unit in self._units:
                row = by_key.get((unit, day))
                if row is None or row.status not in COMPLETE_STATUSES:
                    missing.append(unit)
            if missing:
                self.gaps.append({"data": day, "unidades": missing})
                break
            last_ok = day
        return last_ok


@dataclass(frozen=True)
class CommonCoverageReport:
    units: list[int]
    first_complete: date | None
    last_complete: date | None
    suggested_start: date | None
    suggested_end: date | None
    gaps: list[dict[str, object]]
    empty: bool

    def to_public_payload(self) -> dict[str, object]:
        return {
            "units": list(self.units),
            "firstCompleteDate": self.first_complete.isoformat() if self.first_complete else None,
            "lastCompleteDate": self.last_complete.isoformat() if self.last_complete else None,
            "suggestedStartDate": self.suggested_start.isoformat() if self.suggested_start else None,
            "suggestedEndDate": self.suggested_end.isoformat() if self.suggested_end else None,
            "gaps": list(self.gaps),
            "source": "LOCAL_CHECKPOINT",
            "webpostoWrites": WEBPOSTO_WRITES,
            "empty": self.empty,
        }


def empty_common_coverage(units: list[int], gaps: list[dict[str, object]] | None = None) -> CommonCoverageReport:
    return CommonCoverageReport(
        units=list(units),
        first_complete=None,
        last_complete=None,
        suggested_start=None,
        suggested_end=None,
        gaps=list(gaps or []),
        empty=True,
    )


def _longest_contiguous(days: list[date]) -> tuple[date, date]:
    best = (days[0], days[0])
    run = (days[0], days[0])
    for day in days[1:]:
        if day == run[1] + timedelta(days=1):
            run = (run[0], day)
        else:
            run = (day, day)
        if (run[1] - run[0], run[0]) >= (best[1] - best[0], best[0]):
            best = run
    return best


def common_checkpoint_coverage(store: CheckpointStore, units: list[int]) -> CommonCoverageReport:
    """Interseção diária completa. Não usa MAX(data) isolado nem janela fixa."""
    if not units:
        return empty_common_coverage([])
    rows = store.list_available(units)
    if not rows:
        return empty_common_coverage(units)
    by_key = {(row.empresa_codigo, row.data_referencia): row for row in rows}
    span_start = min(row.data_referencia for row in rows)
    span_end = max(row.data_referencia for row in rows)
    common: list[date] = []
    gaps: list[dict[str, object]] = []
    for day in _daterange(span_start, span_end):
        missing = [
            unit
            for unit in units
            if (
                (row := by_key.get((unit, day))) is None
                or row.status not in COMPLETE_STATUSES
            )
        ]
        if missing:
            gaps.append({"data": day.isoformat(), "unidades": missing})
        else:
            common.append(day)
    if not common:
        return empty_common_coverage(units, gaps)
    suggested_start, suggested_end = _longest_contiguous(common)
    return CommonCoverageReport(
        units=list(units),
        first_complete=common[0],
        last_complete=common[-1],
        suggested_start=suggested_start,
        suggested_end=suggested_end,
        gaps=gaps,
        empty=False,
    )
