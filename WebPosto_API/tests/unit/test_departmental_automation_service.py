import asyncio
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from src.services.departmental_automation_service import DepartmentalAutomationService


class FakePipeline:
    def __init__(self):
        self.calls = []

    async def build_day(self, company, day):
        self.calls.append((company, day))
        return {"companyCode": company, "day": day, "materialized": True, "blockingReasons": []}


class FakeFacts:
    def __init__(self):
        self.saved = []

    def save(self, result):
        self.saved.append(result)


class FakeAlerts:
    def __init__(self):
        self.days = []

    def evaluate(self, day):
        self.days.append(day)


class FakeOperations:
    def weekly_report(self, end):
        return {"period": {"end": end}}


class FakeRadar:
    def __init__(self):
        self.days = []

    def generate(self, day):
        self.days.append(day)
        return {"status": "MONITORING", "priorities": [], "generatedAt": "2026-07-25T09:00:00+00:00"}


class FakeNotifications:
    def dispatch(self, radar):
        return {"created": len(radar["priorities"]), "webhookConfigured": False}


class FakeValueTracker:
    def register_radar(self, radar, agent_briefing=None):
        return {"created": len(radar["priorities"]), "total": len(radar["priorities"])}

    def mark_delivered(self, radar):
        return len(radar["priorities"])


class FakeAgentOrchestrator:
    def coordinate(self, radar):
        return {
            "presidencyAgent": {
                "status": "INSUFFICIENT_EVIDENCE",
                "coordinatedPriorities": [],
            }
        }


def test_daily_job_uses_configured_previous_day_and_is_idempotent(tmp_path):
    config = SimpleNamespace(
        timezone_name="America/Sao_Paulo", daily_enabled=True,
        daily_time=datetime.strptime("06:00", "%H:%M").time(), daily_offset_days=1,
        weekly_enabled=False, weekly_weekday=0,
        weekly_time=datetime.strptime("06:30", "%H:%M").time(), weekly_window_days=7,
        daily_reference_day=lambda day: day.replace(day=24),
    )
    pipeline, facts, alerts, radar = FakePipeline(), FakeFacts(), FakeAlerts(), FakeRadar()
    service = DepartmentalAutomationService(
        config=SimpleNamespace(get=lambda: config), pipeline=pipeline, facts=facts,
        alerts=alerts, operations=FakeOperations(), radar=radar,
        notifications=FakeNotifications(), value_tracker=FakeValueTracker(),
        agent_orchestrator=FakeAgentOrchestrator(),
        state_path=tmp_path / "state.json",
    )
    now = datetime(2026, 7, 25, 6, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    first = asyncio.run(service.run_due(now))
    second = asyncio.run(service.run_due(now))

    assert first["jobs"][0]["status"] == "SUCCESS"
    assert second["jobs"][0]["status"] == "SKIPPED_ALREADY_CLAIMED"
    assert len(pipeline.calls) == 3
    assert alerts.days == ["2026-07-24"]
    assert radar.days == ["2026-07-24"]
    assert first["jobs"][0]["detail"]["proactiveRadar"]["status"] == "MONITORING"
