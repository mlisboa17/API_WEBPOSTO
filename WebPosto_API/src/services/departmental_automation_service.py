"""Executor idempotente das rotinas departamentais configuráveis."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from src.core.management_scope import LICENSED_COMPANIES
from src.gateway.webposto_client import WebPostoClient
from src.services.departmental_alert_service import DepartmentalAlertService
from src.services.departmental_fact_pipeline import DepartmentalFactPipeline
from src.services.departmental_fact_store import DepartmentalFactStore
from src.services.departmental_operations_service import DepartmentalOperationsService
from src.services.departmental_schedule_config_service import DepartmentalScheduleConfigService
from src.services.json_file_lock import InterProcessFileLock
from src.services.proactive_executive_radar_service import ProactiveExecutiveRadarService
from src.services.proactive_notification_service import ProactiveNotificationService
from src.services.proactive_value_service import ProactiveValueService
from src.services.proactive_agent_orchestrator_service import ProactiveAgentOrchestratorService


class DepartmentalAutomationService:
    def __init__(
        self,
        *,
        config=None,
        pipeline=None,
        facts=None,
        alerts=None,
        operations=None,
        radar=None,
        notifications=None,
        value_tracker=None,
        agent_orchestrator=None,
        state_path: str | Path = ".runtime/departmental_automation.json",
    ) -> None:
        self._config = config or DepartmentalScheduleConfigService()
        self._pipeline = pipeline or DepartmentalFactPipeline(WebPostoClient())
        self._facts = facts or DepartmentalFactStore()
        self._alerts = alerts or DepartmentalAlertService()
        self._operations = operations or DepartmentalOperationsService(
            facts=self._facts, alerts=self._alerts
        )
        self._radar = radar or ProactiveExecutiveRadarService(operations=self._operations)
        self._notifications = notifications or ProactiveNotificationService()
        self._value_tracker = value_tracker or ProactiveValueService()
        self._agent_orchestrator = agent_orchestrator or ProactiveAgentOrchestratorService()
        self._path = Path(state_path)

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self._path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {"runs": {}}
        except (OSError, json.JSONDecodeError):
            return {"runs": {}}

    def _save(self, value: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self._path.parent, delete=False
            ) as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
                temp = Path(handle.name)
            os.replace(temp, self._path)
        finally:
            if temp and temp.exists():
                temp.unlink(missing_ok=True)

    def _claim(self, key: str, now: datetime) -> bool:
        with InterProcessFileLock(self._path):
            state = self._load()
            existing = (state.get("runs") or {}).get(key)
            if existing and existing.get("status") == "SUCCESS":
                return False
            if existing and existing.get("status") == "RUNNING":
                try:
                    started = datetime.fromisoformat(existing["startedAt"])
                    if now - started < timedelta(hours=1):
                        return False
                except (KeyError, TypeError, ValueError):
                    return False
            state.setdefault("runs", {})[key] = {
                "status": "RUNNING",
                "startedAt": now.isoformat(),
            }
            self._save(state)
            return True

    def _finish(self, key: str, now: datetime, status: str, detail: dict) -> None:
        with InterProcessFileLock(self._path):
            state = self._load()
            state.setdefault("runs", {})[key] = {
                **(state.get("runs", {}).get(key) or {}),
                "status": status,
                "finishedAt": now.isoformat(),
                "detail": detail,
            }
            self._save(state)

    async def run_due(self, now: datetime | None = None) -> dict[str, Any]:
        config = self._config.get()
        local_now = (now or datetime.now(ZoneInfo(config.timezone_name))).astimezone(
            ZoneInfo(config.timezone_name)
        )
        jobs: list[tuple[str, str, tuple[str, str] | None]] = []
        if config.daily_enabled and local_now.time() >= config.daily_time:
            day = config.daily_reference_day(local_now.date()).isoformat()
            jobs.append((f"daily:{day}", "daily", (day, day)))
        if (
            config.weekly_enabled
            and local_now.weekday() == config.weekly_weekday
            and local_now.time() >= config.weekly_time
        ):
            start, end = config.weekly_window(local_now.date())
            jobs.append((f"weekly:{start}:{end}", "weekly", (start.isoformat(), end.isoformat())))

        results = []
        for key, kind, period in jobs:
            if not self._claim(key, local_now):
                results.append({"key": key, "status": "SKIPPED_ALREADY_CLAIMED"})
                continue
            try:
                if kind == "daily":
                    day = period[0]
                    companies = []
                    for company in LICENSED_COMPANIES:
                        result = await self._pipeline.build_day(company.empresa_codigo, day)
                        if result.get("materialized"):
                            self._facts.save(result)
                        companies.append({
                            "companyCode": company.empresa_codigo,
                            "materialized": bool(result.get("materialized")),
                            "blockingReasons": result.get("blockingReasons") or [],
                        })
                    self._alerts.evaluate(day)
                    radar = self._radar.generate(day)
                    agent_result = self._agent_orchestrator.coordinate(radar)
                    value_result = self._value_tracker.register_radar(radar, agent_result)
                    notification_result = self._notifications.dispatch(radar)
                    delivered = self._value_tracker.mark_delivered(radar)
                    detail = {
                        "period": {"start": day, "end": day},
                        "companies": companies,
                        "proactiveRadar": {
                            "status": radar["status"],
                            "priorityCount": len(radar["priorities"]),
                            "generatedAt": radar["generatedAt"],
                        },
                        "proactiveNotifications": notification_result,
                        "valueTracking": {**value_result, "delivered": delivered},
                        "proactiveAgents": {
                            "presidencyStatus": agent_result["presidencyAgent"]["status"],
                            "coordinatedPriorityCount": len(
                                agent_result["presidencyAgent"]["coordinatedPriorities"]
                            ),
                        },
                    }
                else:
                    detail = self._operations.weekly_report(period[1])
                self._finish(key, local_now, "SUCCESS", detail)
                results.append({"key": key, "status": "SUCCESS", "detail": detail})
            except Exception as exc:  # noqa: BLE001
                detail = {"error": str(exc)[:300]}
                self._finish(key, local_now, "FAILED", detail)
                results.append({"key": key, "status": "FAILED", "detail": detail})
        return {"checkedAt": local_now.isoformat(), "jobs": results}

    def history(self) -> list[dict[str, Any]]:
        runs = self._load().get("runs") or {}
        return [{"key": key, **value} for key, value in sorted(runs.items(), reverse=True)]


_automation: DepartmentalAutomationService | None = None


def get_departmental_automation() -> DepartmentalAutomationService:
    global _automation
    if _automation is None:
        _automation = DepartmentalAutomationService()
    return _automation
