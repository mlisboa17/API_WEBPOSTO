"""Agentes executivos especializados e coordenador governado da Presidência."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.services.json_file_lock import InterProcessFileLock


INSUFFICIENT_EVIDENCE = "Não existem evidências suficientes para produzir uma recomendação confiável."


class ProactiveAgentOrchestratorService:
    def __init__(self, root: str | Path = ".runtime/proactive_agents") -> None:
        self._root = Path(root)
        self._agents: tuple[tuple[str, Callable[[dict], bool]], ...] = (
            ("FINANCIAL", self._financial),
            ("OPERATIONAL", self._operational),
            ("COMMERCIAL", self._commercial),
            ("GOVERNANCE", self._governance),
        )

    def coordinate(self, radar: dict[str, Any]) -> dict[str, Any]:
        priorities = radar.get("priorities") or []
        briefs = [
            self._brief(name, [item for item in priorities if matcher(item)])
            for name, matcher in self._agents
        ]
        candidates: dict[str, dict] = {}
        for brief in briefs:
            for item in brief["recommendations"]:
                if item["id"] not in candidates:
                    candidates[item["id"]] = {
                        **item,
                        "contributingAgents": [brief["agent"]],
                    }
                else:
                    candidates[item["id"]]["contributingAgents"].append(brief["agent"])
        coordinated = sorted(
            candidates.values(),
            key=lambda item: (-float(item["priorityScore"]), item["id"]),
        )[:5]
        result = {
            "schemaVersion": 1,
            "day": radar["day"],
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "specialistAgents": briefs,
            "presidencyAgent": {
                "status": "ACTION_REQUIRED" if coordinated else "INSUFFICIENT_EVIDENCE",
                "message": None if coordinated else INSUFFICIENT_EVIDENCE,
                "coordinatedPriorities": coordinated,
                "conflicts": [],
                "newFactsCreated": False,
                "confidenceElevated": False,
            },
            "governance": {
                "sourceRadarDay": radar["day"],
                "sourceRadarGeneratedAt": radar["generatedAt"],
                "evidenceRequired": True,
                "lineageRequired": True,
                "justificationRequired": True,
                "confidenceRequired": True,
                "humanReviewRequired": True,
                "automaticExecution": False,
            },
        }
        self._save(radar["day"], result)
        return result

    def get(self, day: str) -> dict[str, Any] | None:
        try:
            value = json.loads((self._root / f"{day}.json").read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def latest(self) -> dict[str, Any] | None:
        files = sorted(self._root.glob("????-??-??.json"), reverse=True)
        return self.get(files[0].stem) if files else None

    @staticmethod
    def _brief(name: str, matches: list[dict]) -> dict[str, Any]:
        valid = [
            item for item in matches
            if item.get("evidence")
            and item.get("lineage")
            and item.get("confidence")
            and item.get("recommendedAction")
        ]
        recommendations = [{
            **item,
            "agent": name,
            "justification": (
                f"Selecionado pelo Agente {name.title()} com base na regra "
                f"{item['lineage'].get('rule', 'homologada')} e na evidência vinculada."
            ),
        } for item in valid]
        return {
            "agent": name,
            "status": "RECOMMENDATIONS_AVAILABLE" if recommendations else "INSUFFICIENT_EVIDENCE",
            "message": None if recommendations else INSUFFICIENT_EVIDENCE,
            "recommendations": recommendations,
            "rejectedWithoutGovernance": len(matches) - len(valid),
        }

    @staticmethod
    def _financial(item: dict) -> bool:
        return item.get("lineage", {}).get("rule") in {
            "NEGATIVE_GROSS_MARGIN",
            "EXPENSE_CLASSIFICATION_INCOMPLETE",
        }

    @staticmethod
    def _operational(item: dict) -> bool:
        return (
            item.get("department") == "combustiveis"
            or item.get("lineage", {}).get("rule") in {
                "MATERIALIZATION_MISSING",
                "FINANCIAL_COVERAGE_INCOMPLETE",
            }
        )

    @staticmethod
    def _commercial(item: dict) -> bool:
        return item.get("department") in {"conveniencia", "lubrificantes"} or item.get("type") == "OPPORTUNITY"

    @staticmethod
    def _governance(item: dict) -> bool:
        return item.get("severity") == "CRITICAL" or "INCOMPLETE" in str(item.get("lineage", {}).get("rule"))

    def _save(self, day: str, value: dict[str, Any]) -> None:
        target = self._root / f"{day}.json"
        with InterProcessFileLock(target):
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary: Path | None = None
            try:
                with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as handle:
                    json.dump(value, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                    temporary = Path(handle.name)
                os.replace(temporary, target)
            finally:
                if temporary:
                    temporary.unlink(missing_ok=True)
