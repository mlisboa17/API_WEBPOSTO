"""Decisao de politica: sempre explicita, nunca escondida em script de onda."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..versions import POLICY_DECISION_SCHEMA_VERSION


class PolicyDecision(BaseModel):
    """Registro padronizado de uma decisao de politica."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = POLICY_DECISION_SCHEMA_VERSION
    policy_name: str
    policy_version: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    decision: str
    confidence: str = "NONE"
    reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    owner_risk_accepted: bool = False
    requires_review: bool = False
    allowed: bool = True
