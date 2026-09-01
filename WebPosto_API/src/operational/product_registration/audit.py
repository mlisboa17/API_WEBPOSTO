"""Trilha de auditoria sanitizada e versionada."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .policies.cost_policy import CostPolicy
from .versions import AUDIT_EVENT_SCHEMA_VERSION, ENGINE_VERSION


class RegistrationAuditTrail:
    """Eventos estruturados. Nunca armazena credencial ou chave de NF-e completa."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self._cost = CostPolicy()

    def record(
        self,
        event_type: str,
        *,
        ean: str | None = None,
        decision: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "audit_event_schema_version": AUDIT_EVENT_SCHEMA_VERSION,
            "engine_version": ENGINE_VERSION,
            "event_type": event_type,
            "ean": ean,
            "at": datetime.now(timezone.utc).isoformat(),
            "decision": decision,
            "extra": self._cost.sanitize_evidence(extra or {}),
        }
        self.events.append(event)
        return event
