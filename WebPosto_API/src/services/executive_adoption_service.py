"""Telemetria mínima e não sensível da experiência executiva."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.services.json_file_lock import InterProcessFileLock


class ExecutiveAdoptionService:
    ALLOWED_EVENTS = {"PAGE_OPEN", "INFORMATION_FOUND", "FEATURE_USED"}
    ALLOWED_FEATURES = {"ATTENTION", "VALUE", "AI_VALUE", "PRESIDENCY_ANSWERS", "DETAILS"}

    def __init__(self, path: str | Path = ".runtime/executive_adoption.json") -> None:
        self._path = Path(path)

    def record(self, event: dict[str, Any]) -> dict[str, Any]:
        event_type = str(event.get("eventType", "")).upper()
        feature = str(event.get("feature", "")).upper()
        if event_type not in self.ALLOWED_EVENTS or feature not in self.ALLOWED_FEATURES:
            raise ValueError("INVALID_ADOPTION_EVENT")
        elapsed = event.get("elapsedMs")
        clicks = event.get("clicks")
        record = {
            "eventType": event_type,
            "feature": feature,
            "sessionId": str(event.get("sessionId", ""))[:80],
            "elapsedMs": max(0, min(int(elapsed), 3_600_000)) if elapsed is not None else None,
            "clicks": max(0, min(int(clicks), 100)) if clicks is not None else None,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        with InterProcessFileLock(self._path):
            state = self._load()
            state.setdefault("events", []).append(record)
            state["events"] = state["events"][-10000:]
            self._save(state)
        return record

    def summary(self) -> dict[str, Any]:
        events = self._load().get("events") or []
        found = [item for item in events if item["eventType"] == "INFORMATION_FOUND"]
        usage: dict[str, int] = {}
        for item in events:
            if item["eventType"] == "FEATURE_USED":
                usage[item["feature"]] = usage.get(item["feature"], 0) + 1
        return {
            "sessions": len({item["sessionId"] for item in events if item["sessionId"]}),
            "averageTimeToInformationMs": round(
                sum(item["elapsedMs"] or 0 for item in found) / len(found), 2
            ) if found else None,
            "averageClicksToInformation": round(
                sum(item["clicks"] or 0 for item in found) / len(found), 2
            ) if found else None,
            "featureUsage": usage,
            "ignoredFeatures": sorted(self.ALLOWED_FEATURES - set(usage)),
            "containsBusinessData": False,
        }

    def _load(self) -> dict:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schemaVersion": 1, "events": []}

    def _save(self, value: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self._path.parent, delete=False) as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
                temporary = Path(handle.name)
            os.replace(temporary, self._path)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
