"""Radar executivo proativo baseado somente em fatos e alertas governados."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.services.departmental_operations_service import DepartmentalOperationsService
from src.services.json_file_lock import InterProcessFileLock


class ProactiveExecutiveRadarService:
    WEIGHTS = {
        "financialImpact": 0.35,
        "strategicImpact": 0.25,
        "executiveTimeSaving": 0.20,
        "riskReduction": 0.15,
        "implementationEase": 0.05,
    }

    def __init__(
        self,
        operations: DepartmentalOperationsService | None = None,
        root: str | Path = ".runtime/proactive_executive_radar",
    ) -> None:
        self._operations = operations or DepartmentalOperationsService()
        self._root = Path(root)

    def generate(self, day: str) -> dict[str, Any]:
        current = self._operations.daily_report(day)
        previous_day = (date.fromisoformat(day) - timedelta(days=1)).isoformat()
        previous_health = self._operations.health(previous_day)
        changes = self._changes(current["health"], previous_health)
        insights = [self._insight(alert) for alert in current["alerts"]]
        insights.sort(key=lambda item: (-item["priorityScore"], item["id"]))
        payload = {
            "schemaVersion": 1,
            "kind": "DAILY_EXECUTIVE_RADAR",
            "day": day,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "audiences": ["PRESIDENT", "PARTNER", "BOARD", "DIRECTOR", "EXECUTIVE_MANAGER"],
            "status": "ACTION_REQUIRED" if insights else (
                "DATA_QUALITY_BLOCKED" if current["health"]["status"] != "HEALTHY" else "MONITORING"
            ),
            "whatChanged24h": changes,
            "priorities": insights[:5],
            "executiveAnswers": self._answers(insights, current),
            "governance": {
                "source": "WebPosto departmental facts and governed alerts",
                "humanReviewRequired": True,
                "automaticExecution": False,
                "unsupportedDomains": ["customers", "contracts", "churn", "strategicProjects"],
                "prioritizationWeights": self.WEIGHTS,
            },
        }
        self._save(day, payload)
        return payload

    def get(self, day: str) -> dict[str, Any] | None:
        path = self._root / f"{day}.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def latest(self) -> dict[str, Any] | None:
        files = sorted(self._root.glob("????-??-??.json"), reverse=True)
        return self.get(files[0].stem) if files else None

    @classmethod
    def _insight(cls, alert: dict[str, Any]) -> dict[str, Any]:
        severity = alert.get("severity")
        impact = alert.get("estimatedImpactBRL")
        scores = {
            "financialImpact": min(100, float(impact) / 100) if impact is not None else (65 if severity == "CRITICAL" else 35),
            "strategicImpact": 90 if severity == "CRITICAL" else 60,
            "executiveTimeSaving": 70,
            "riskReduction": 95 if severity == "CRITICAL" else 65,
            "implementationEase": 75,
        }
        priority = round(sum(scores[key] * weight for key, weight in cls.WEIGHTS.items()), 2)
        return {
            "id": alert["id"],
            "type": "RISK",
            "title": alert["message"],
            "companyCode": alert["companyCode"],
            "department": alert["department"],
            "severity": severity,
            "estimatedImpactBRL": impact,
            "impactLabel": "ESTIMATED_FROM_EVIDENCE" if impact is not None else "NOT_QUANTIFIED",
            "suggestedOwner": alert["suggestedOwner"],
            "recommendedAction": "Revisar a evidência, confirmar a causa e registrar o tratamento do alerta.",
            "dueInDays": alert["dueInDays"],
            "confidence": "HIGH" if impact is not None else "MEDIUM",
            "priorityScore": priority,
            "scoreBreakdown": scores,
            "evidence": alert["evidence"],
            "lineage": {"alertId": alert["id"], "rule": alert["rule"], "period": alert["period"]},
        }

    @staticmethod
    def _changes(current: dict, previous: dict) -> list[dict[str, Any]]:
        before = {item["companyCode"]: item for item in previous["companies"]}
        changes = []
        for item in current["companies"]:
            old = before.get(item["companyCode"]) or {}
            fields = {
                "referenceDayAvailable": (old.get("referenceDayAvailable"), item["referenceDayAvailable"]),
                "publishable": (old.get("publishable"), item["publishable"]),
                "blockingReasons": (old.get("blockingReasons"), item["blockingReasons"]),
            }
            changed = {key: {"before": values[0], "after": values[1]} for key, values in fields.items() if values[0] != values[1]}
            if changed:
                changes.append({"companyCode": item["companyCode"], "changes": changed})
        return changes

    @staticmethod
    def _answers(insights: list[dict], report: dict) -> dict[str, Any]:
        top = insights[0] if insights else None
        loss = next((item for item in insights if item["lineage"]["rule"] == "NEGATIVE_GROSS_MARGIN"), None)
        return {
            "largestRisk": top,
            "whereLosingMoney": loss or {"status": "INSUFFICIENT_EQUIVALENT_DATA"},
            "fastestGrowthOpportunity": {"status": "INSUFFICIENT_EQUIVALENT_DATA"},
            "leadersNeedingSupport": sorted({item["suggestedOwner"] for item in insights}),
            "immediateDecisions": insights[:3],
            "dataCoverage": report["health"]["status"],
        }

    def _save(self, day: str, payload: dict) -> None:
        target = self._root / f"{day}.json"
        with InterProcessFileLock(target):
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary: Path | None = None
            try:
                with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as handle:
                    json.dump(payload, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                    temporary = Path(handle.name)
                os.replace(temporary, target)
            finally:
                if temporary:
                    temporary.unlink(missing_ok=True)
