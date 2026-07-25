"""Aprendizado dos agentes baseado exclusivamente em valor observado e validado."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.services.json_file_lock import InterProcessFileLock


VALUE_KEYS = (
    "revenueGeneratedBRL",
    "costAvoidedBRL",
    "riskMitigatedBRL",
    "executiveHoursSaved",
)
STATUS_ORDER = ("GENERATED", "DELIVERED", "VIEWED", "ACCEPTED", "IMPLEMENTED", "VALIDATED")
LEGACY_STATUS = {"EXECUTED": "IMPLEMENTED", "CONFIRMED": "VALIDATED"}


class ProactiveValueService:
    EVS_WEIGHTS = {
        "financialImpact": 0.30,
        "riskReduction": 0.25,
        "operationalEfficiency": 0.15,
        "decisionSpeed": 0.15,
        "adoption": 0.15,
    }
    RELIABILITY_WEIGHTS = {
        "historicalPrecision": 0.35,
        "acceptanceRate": 0.20,
        "implementationRate": 0.20,
        "validatedResultRate": 0.25,
    }

    def __init__(self, path: str | Path = ".runtime/proactive_value.json") -> None:
        self._path = Path(path)

    def register_radar(
        self,
        radar: dict[str, Any],
        agent_briefing: dict[str, Any] | None = None,
    ) -> dict[str, int]:
        contributors = {
            item["id"]: item.get("contributingAgents") or [item.get("agent")]
            for item in ((agent_briefing or {}).get("presidencyAgent", {}).get("coordinatedPriorities") or [])
        }
        created = 0
        with InterProcessFileLock(self._path):
            state = self._load()
            records = state.setdefault("recommendations", {})
            for insight in radar.get("priorities") or []:
                recommendation_id = f"{radar['day']}:{insight['id']}"
                if recommendation_id in records:
                    continue
                records[recommendation_id] = {
                    "id": recommendation_id,
                    "sourceInsightId": insight["id"],
                    "day": radar["day"],
                    "status": "GENERATED",
                    "title": insight["title"],
                    "type": insight["type"],
                    "agents": [agent for agent in contributors.get(insight["id"], []) if agent],
                    "estimatedImpactBRL": insight.get("estimatedImpactBRL"),
                    "confidence": insight["confidence"],
                    "lineage": insight["lineage"],
                    "generatedAt": radar["generatedAt"],
                    "events": [],
                    "validatedValue": None,
                    "falsePositive": False,
                }
                created += 1
            self._save(state)
        return {"created": created, "total": len(radar.get("priorities") or [])}

    def mark_delivered(self, radar: dict[str, Any], evidence: str = "Notificação disponibilizada na outbox") -> int:
        changed = 0
        with InterProcessFileLock(self._path):
            state = self._load()
            records = state.get("recommendations") or {}
            for insight in radar.get("priorities") or []:
                record = records.get(f"{radar['day']}:{insight['id']}")
                if record and self._status(record) == "GENERATED":
                    self._apply_event(record, "DELIVERED", "system", evidence)
                    changed += 1
            if changed:
                self._save(state)
        return changed

    def transition(
        self,
        recommendation_id: str,
        action: str,
        actor: str,
        evidence: str,
        validated_value: dict[str, float] | None = None,
        false_positive: bool = False,
    ) -> dict[str, Any] | None:
        if len(evidence.strip()) < 3:
            raise ValueError("EVIDENCE_REQUIRED")
        target = LEGACY_STATUS.get(action.upper(), action.upper())
        allowed = {
            ("DELIVERED", "VIEWED"),
            ("VIEWED", "ACCEPTED"),
            ("VIEWED", "REJECTED"),
            ("ACCEPTED", "IMPLEMENTED"),
            ("IMPLEMENTED", "VALIDATED"),
        }
        with InterProcessFileLock(self._path):
            state = self._load()
            record = (state.get("recommendations") or {}).get(recommendation_id)
            if not record:
                return None
            current = self._status(record)
            if (current, target) not in allowed:
                raise ValueError("INVALID_RECOMMENDATION_TRANSITION")
            if target == "VALIDATED":
                values = validated_value or {}
                normalized = {key: max(0.0, float(values.get(key, 0))) for key in VALUE_KEYS}
                if not any(normalized.values()):
                    raise ValueError("VALIDATED_VALUE_REQUIRED")
                record["validatedValue"] = normalized
                record["confirmedValue"] = normalized
            if target == "REJECTED":
                record["falsePositive"] = bool(false_positive)
            self._apply_event(record, target, actor, evidence)
            self._save(state)
            return record

    def summary(self, month: str | None = None) -> dict[str, Any]:
        records = self._records(month)
        validated = [item for item in records if self._status(item) == "VALIDATED" and self._value(item)]
        values = {
            key: round(sum(self._value(item)[key] for item in validated), 2)
            for key in VALUE_KEYS
        }
        generated = len(records)
        accepted = sum(self._reached(item, "ACCEPTED") for item in records)
        implemented = sum(self._reached(item, "IMPLEMENTED") for item in records)
        potential = round(sum(float(item.get("estimatedImpactBRL") or 0) for item in records), 2)
        components = self._evs_components(records, values, implemented, generated)
        evs = round(sum(components[key] * weight for key, weight in self.EVS_WEIGHTS.items()), 2)
        agent_metrics = self._agent_metrics(records)
        top_agent = max(
            agent_metrics,
            key=lambda item: item["attributedValidatedValueBRL"],
            default=None,
        )
        if top_agent and top_agent["attributedValidatedValueBRL"] <= 0:
            top_agent = None
        top_recommendations = sorted(
            [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "agents": item.get("agents") or [],
                    "validatedValueBRL": self._financial_value(self._value(item)),
                }
                for item in validated
            ],
            key=lambda item: -item["validatedValueBRL"],
        )[:5]
        return {
            "period": month or "ALL",
            "recommendations": {
                "generated": generated,
                "delivered": sum(self._reached(item, "DELIVERED") for item in records),
                "viewed": sum(self._reached(item, "VIEWED") for item in records),
                "accepted": accepted,
                "rejected": sum(self._status(item) == "REJECTED" for item in records),
                "implemented": implemented,
                "validated": len(validated),
            },
            "estimatedValue": {"potentialValueBRL": potential, "label": "ESTIMATED_NOT_REALIZED"},
            "businessValueGeneratedByAI": {
                **values,
                "totalFinancialValueBRL": round(
                    values["revenueGeneratedBRL"] + values["costAvoidedBRL"], 2
                ),
                "label": "VALIDATED_VALUE_ONLY",
            },
            "confirmedValue": values,
            "potentialValueBRL": potential,
            "adoptionRate": round(implemented / generated * 100, 2) if generated else 0.0,
            "topContributingAgent": top_agent,
            "highestImpactRecommendations": top_recommendations,
            "agentMetrics": agent_metrics,
            "executiveValueScore": {
                "score": evs,
                "components": components,
                "weights": self.EVS_WEIGHTS,
                "label": "CONFIRMED_VALUE_ONLY",
            },
        }

    def list(self, month: str | None = None) -> list[dict[str, Any]]:
        return sorted(self._records(month), key=lambda item: item["generatedAt"], reverse=True)

    def monthly_report(self, month: str) -> dict[str, Any]:
        if len(month) != 7 or month[4] != "-":
            raise ValueError("INVALID_MONTH")
        summary = self.summary(month)
        validated = summary["businessValueGeneratedByAI"]
        estimated = summary["estimatedValue"]
        recommendations = self.list(month)
        return {
            "reportType": "MONTHLY_BUSINESS_VALUE_GENERATED_BY_AI",
            "period": month,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "headline": (
                f"Valor financeiro comprovado no período: R$ {validated['totalFinancialValueBRL']:,.2f}"
                if validated["totalFinancialValueBRL"] > 0
                else "Nenhum valor validado registrado no período — potencial estimado não é realizado."
            ),
            "businessValueGeneratedByAI": validated,
            "estimatedValue": estimated,
            "recommendationFunnel": summary["recommendations"],
            "executiveValueScore": summary["executiveValueScore"],
            "topContributingAgent": summary["topContributingAgent"],
            "highestImpactRecommendations": summary["highestImpactRecommendations"],
            "agentMetrics": summary["agentMetrics"],
            "adoptionRate": summary["adoptionRate"],
            "items": [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "status": self._status(item),
                    "agents": item.get("agents") or [],
                    "estimatedImpactBRL": item.get("estimatedImpactBRL"),
                    "validatedValue": item.get("validatedValue"),
                    "falsePositive": item.get("falsePositive", False),
                }
                for item in recommendations
            ],
            "governance": {
                "validatedOnlyInTotals": True,
                "estimatedNeverCountedAsRealized": True,
                "scopeCompanies": ["11495", "5555", "74014"],
            },
        }

    def _agent_metrics(self, records: list[dict]) -> list[dict[str, Any]]:
        names = ("FINANCIAL", "OPERATIONAL", "COMMERCIAL", "GOVERNANCE")
        output = []
        for name in names:
            owned = [item for item in records if name in (item.get("agents") or [])]
            delivered = sum(self._reached(item, "DELIVERED") for item in owned)
            accepted = sum(self._reached(item, "ACCEPTED") for item in owned)
            implemented = sum(self._reached(item, "IMPLEMENTED") for item in owned)
            validated = [item for item in owned if self._status(item) == "VALIDATED"]
            false_positives = sum(
                self._status(item) == "REJECTED" and item.get("falsePositive") is True
                for item in owned
            )
            precision_base = len(validated) + false_positives
            components = {
                "historicalPrecision": round(len(validated) / precision_base * 100, 2) if precision_base else None,
                "acceptanceRate": round(accepted / delivered * 100, 2) if delivered else None,
                "implementationRate": round(implemented / accepted * 100, 2) if accepted else None,
                "validatedResultRate": round(len(validated) / implemented * 100, 2) if implemented else None,
            }
            reliability = None
            if precision_base:
                reliability = round(sum(
                    (components[key] or 0) * weight
                    for key, weight in self.RELIABILITY_WEIGHTS.items()
                ), 2)
            attributed = 0.0
            for item in validated:
                agents = item.get("agents") or [name]
                value = self._value(item)
                attributed += (
                    self._financial_value(value) + value["riskMitigatedBRL"]
                ) / max(1, len(agents))
            output.append({
                "agent": name,
                "recommendationsGenerated": len(owned),
                "accepted": accepted,
                "implemented": implemented,
                "validated": len(validated),
                "falsePositives": false_positives,
                "attributedValidatedValueBRL": round(attributed, 2),
                "reliability": {
                    "score": reliability,
                    "status": "CALCULATED_FROM_OBSERVED_RESULTS" if reliability is not None else "INSUFFICIENT_VALIDATED_OUTCOMES",
                    "components": components,
                    "weights": self.RELIABILITY_WEIGHTS,
                },
            })
        return output

    @staticmethod
    def _value(record: dict) -> dict[str, float]:
        value = record.get("validatedValue") or record.get("confirmedValue") or {}
        return {key: float(value.get(key, 0)) for key in VALUE_KEYS}

    @staticmethod
    def _financial_value(value: dict[str, float]) -> float:
        return value["revenueGeneratedBRL"] + value["costAvoidedBRL"]

    @staticmethod
    def _status(record: dict) -> str:
        return LEGACY_STATUS.get(record.get("status"), record.get("status", "GENERATED"))

    @classmethod
    def _reached(cls, record: dict, target: str) -> bool:
        status = cls._status(record)
        if status == "REJECTED":
            return target in ("DELIVERED", "VIEWED")
        return STATUS_ORDER.index(status) >= STATUS_ORDER.index(target)

    @staticmethod
    def _apply_event(record: dict, target: str, actor: str, evidence: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        record["status"] = target
        record[f"{target.lower()}At"] = now
        record.setdefault("events", []).append({
            "action": target,
            "actor": actor,
            "evidence": evidence.strip(),
            "at": now,
        })

    @staticmethod
    def _evs_components(records: list[dict], values: dict, implemented: int, generated: int) -> dict[str, float]:
        financial = values["revenueGeneratedBRL"] + values["costAvoidedBRL"]
        validated = [item for item in records if item.get("validatedAt") or item.get("confirmedAt")]
        durations = []
        for item in validated:
            start = datetime.fromisoformat(item["generatedAt"])
            end = datetime.fromisoformat(item.get("validatedAt") or item["confirmedAt"])
            durations.append(max(0.0, (end - start).total_seconds() / 3600))
        average_hours = sum(durations) / len(durations) if durations else None
        return {
            "financialImpact": round(min(100, financial / 100), 2),
            "riskReduction": round(min(100, values["riskMitigatedBRL"] / 100), 2),
            "operationalEfficiency": round(min(100, values["executiveHoursSaved"] * 5), 2),
            "decisionSpeed": round(max(0, 100 - average_hours / 0.72), 2) if average_hours is not None else 0.0,
            "adoption": round(implemented / generated * 100, 2) if generated else 0.0,
        }

    def _records(self, month: str | None) -> list[dict[str, Any]]:
        records = list((self._load().get("recommendations") or {}).values())
        return [item for item in records if not month or item.get("day", "").startswith(month)]

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self._path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {"recommendations": {}}
        except (OSError, json.JSONDecodeError):
            return {"schemaVersion": 2, "recommendations": {}}

    def _save(self, value: dict[str, Any]) -> None:
        value["schemaVersion"] = 2
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
