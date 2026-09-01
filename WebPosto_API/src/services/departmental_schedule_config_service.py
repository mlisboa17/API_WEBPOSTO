"""Configuração governada das rotinas departamentais diária e semanal."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.services.json_file_lock import InterProcessFileLock


DEFAULT_PATH = Path(".runtime/departmental_schedule.json")


class DepartmentalScheduleConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    timezone_name: str = "America/Sao_Paulo"
    daily_enabled: bool = True
    daily_time: time = time(6, 0)
    daily_offset_days: int = Field(default=1, ge=1, le=7)
    weekly_enabled: bool = False
    weekly_weekday: int = Field(default=0, ge=0, le=6)
    weekly_time: time = time(6, 30)
    weekly_window_days: int = Field(default=7, ge=1, le=31)
    updated_at: datetime | None = None
    updated_by: str | None = None

    @field_validator("timezone_name")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("INVALID_TIMEZONE") from exc
        return value

    def daily_reference_day(self, execution_day: date) -> date:
        return execution_day - timedelta(days=self.daily_offset_days)

    def weekly_window(self, execution_day: date) -> tuple[date, date]:
        end = execution_day - timedelta(days=1)
        return end - timedelta(days=self.weekly_window_days - 1), end


class DepartmentalScheduleConfigService:
    def __init__(self, path: str | Path = DEFAULT_PATH) -> None:
        self._path = Path(path)

    def get(self) -> DepartmentalScheduleConfig:
        if not self._path.exists():
            return DepartmentalScheduleConfig()
        try:
            return DepartmentalScheduleConfig.model_validate_json(
                self._path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return DepartmentalScheduleConfig()

    def update(self, values: dict, actor: str) -> DepartmentalScheduleConfig:
        with InterProcessFileLock(self._path):
            current = self.get()
            updated = DepartmentalScheduleConfig.model_validate(
                {
                    **current.model_dump(),
                    **values,
                    "updated_at": datetime.now(timezone.utc),
                    "updated_by": actor,
                }
            )
            self._save(updated)
            return updated

    def _save(self, config: DepartmentalScheduleConfig) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self._path.parent, delete=False
            ) as handle:
                handle.write(config.model_dump_json(indent=2))
                handle.flush()
                os.fsync(handle.fileno())
                temp = Path(handle.name)
            os.replace(temp, self._path)
        finally:
            if temp and temp.exists():
                temp.unlink(missing_ok=True)
