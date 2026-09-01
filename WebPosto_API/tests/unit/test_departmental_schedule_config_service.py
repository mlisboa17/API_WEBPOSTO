from datetime import date

import pytest

from src.services.departmental_schedule_config_service import (
    DepartmentalScheduleConfigService,
)


def test_default_schedule_uses_previous_day_at_six(tmp_path):
    config = DepartmentalScheduleConfigService(tmp_path / "schedule.json").get()

    assert config.timezone_name == "America/Sao_Paulo"
    assert config.daily_time.isoformat() == "06:00:00"
    assert config.daily_reference_day(date(2026, 7, 25)) == date(2026, 7, 24)
    assert config.weekly_enabled is False


def test_user_can_configure_daily_and_weekly_schedule(tmp_path):
    service = DepartmentalScheduleConfigService(tmp_path / "schedule.json")
    config = service.update(
        {
            "daily_time": "07:15",
            "daily_offset_days": 2,
            "weekly_enabled": True,
            "weekly_weekday": 4,
            "weekly_time": "08:30",
            "weekly_window_days": 14,
        },
        "diretoria",
    )

    persisted = service.get()
    assert persisted == config
    assert persisted.daily_reference_day(date(2026, 7, 25)) == date(2026, 7, 23)
    assert persisted.weekly_window(date(2026, 7, 25)) == (
        date(2026, 7, 11),
        date(2026, 7, 24),
    )
    assert persisted.updated_by == "diretoria"


def test_invalid_timezone_is_rejected(tmp_path):
    service = DepartmentalScheduleConfigService(tmp_path / "schedule.json")

    with pytest.raises(ValueError, match="INVALID_TIMEZONE"):
        service.update({"timezone_name": "Invalid/Timezone"}, "diretoria")
