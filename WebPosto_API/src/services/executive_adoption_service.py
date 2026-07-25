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
    BLOCK_LABELS = {
        "ATTENTION": "O que exige atenção hoje",
        "VALUE": "O que gera mais valor",
        "AI_VALUE": "Valor gerado pela IA",
        "PRESIDENCY_ANSWERS": "Perguntas da Presidência",
        "DETAILS": "Análises detalhadas",
    }
    THIRTY_SECOND_TARGET_MS = 30_000

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
        avg_ms = round(sum(item["elapsedMs"] or 0 for item in found) / len(found), 2) if found else None
        return {
            "sessions": len({item["sessionId"] for item in events if item["sessionId"]}),
            "averageTimeToInformationMs": avg_ms,
            "averageClicksToInformation": round(
                sum(item["clicks"] or 0 for item in found) / len(found), 2
            ) if found else None,
            "featureUsage": usage,
            "ignoredFeatures": sorted(self.ALLOWED_FEATURES - set(usage)),
            "withinThirtySecondTarget": avg_ms is not None and avg_ms <= self.THIRTY_SECOND_TARGET_MS,
            "containsBusinessData": False,
        }

    def block_review(self) -> dict[str, Any]:
        events = self._load().get("events") or []
        usage = {
            feature: {"opens": 0, "informationFound": 0, "timesMs": [], "clicks": []}
            for feature in self.ALLOWED_FEATURES
        }
        for item in events:
            feature = item["feature"]
            if feature not in usage:
                continue
            if item["eventType"] in {"FEATURE_USED", "PAGE_OPEN"}:
                usage[feature]["opens"] += 1
            if item["eventType"] == "INFORMATION_FOUND":
                usage[feature]["informationFound"] += 1
                if item.get("elapsedMs") is not None:
                    usage[feature]["timesMs"].append(item["elapsedMs"])
                if item.get("clicks") is not None:
                    usage[feature]["clicks"].append(item["clicks"])
        blocks = []
        for feature in ("ATTENTION", "VALUE", "AI_VALUE", "PRESIDENCY_ANSWERS"):
            stats = usage[feature]
            avg_ms = round(sum(stats["timesMs"]) / len(stats["timesMs"]), 2) if stats["timesMs"] else None
            avg_clicks = round(sum(stats["clicks"]) / len(stats["clicks"]), 2) if stats["clicks"] else None
            engagement = "IGNORED" if stats["opens"] == 0 else (
                "ENGAGED" if stats["informationFound"] else "OPENED_ONLY"
            )
            blocks.append({
                "feature": feature,
                "title": self.BLOCK_LABELS[feature],
                "engagement": engagement,
                "opens": stats["opens"],
                "informationFound": stats["informationFound"],
                "averageTimeToInformationMs": avg_ms,
                "averageClicks": avg_clicks,
                "withinThirtySecondTarget": avg_ms is not None and avg_ms <= self.THIRTY_SECOND_TARGET_MS,
            })
        ignored = [block for block in blocks if block["engagement"] == "IGNORED"]
        return {
            "blocks": blocks,
            "presidencyBlocksReviewed": len(blocks),
            "ignoredPresidencyBlocks": [block["feature"] for block in ignored],
            "recommendations": [
                f"Revisar copy e hierarquia do bloco {block['title']} — nunca aberto nas sessões observadas."
                for block in ignored
            ] + [
                f"Reduzir fricção no bloco {block['title']}; tempo médio {block['averageTimeToInformationMs']}ms excede 30s."
                for block in blocks
                if block["averageTimeToInformationMs"] is not None
                and block["averageTimeToInformationMs"] > self.THIRTY_SECOND_TARGET_MS
            ],
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
