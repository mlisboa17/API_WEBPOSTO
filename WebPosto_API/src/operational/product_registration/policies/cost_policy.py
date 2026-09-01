"""Politica de custo: somente DF-e, nunca template, semelhante ou margem."""

from __future__ import annotations

from typing import Any

from .decision import PolicyDecision

POLICY_NAME = "cost_policy"
POLICY_VERSION = "1.0.0"
PENDING_COST_STATUS = "PENDING"


class CostPolicy:
    """Avalia se o custo pode ir no body e sob qual autorizacao."""

    name = POLICY_NAME
    version = POLICY_VERSION

    def evaluate(
        self,
        *,
        cost: float | None,
        cost_source: str | None,
        cost_status: str | None,
        sale_price: float | None,
        allow_pending_dfe_cost: bool,
        accept_negative_margin: bool = False,
    ) -> PolicyDecision:
        inputs = {
            "cost": cost,
            "cost_source": cost_source,
            "cost_status": cost_status,
            "sale_price": sale_price,
            "allow_pending_dfe_cost": allow_pending_dfe_cost,
            "accept_negative_margin": accept_negative_margin,
        }
        if cost is None:
            return PolicyDecision(
                policy_name=POLICY_NAME,
                policy_version=POLICY_VERSION,
                inputs=inputs,
                decision="CUSTO_AUSENTE",
                confidence="NONE",
                reasons=["Custo nao informado"],
                allowed=False,
                requires_review=True,
            )
        value = float(cost)
        if value < 0:
            return PolicyDecision(
                policy_name=POLICY_NAME,
                policy_version=POLICY_VERSION,
                inputs=inputs,
                decision="CUSTO_NEGATIVO",
                reasons=["Custo negativo e invalido"],
                allowed=False,
            )
        if value > 0:
            if cost_source != "DFE":
                return PolicyDecision(
                    policy_name=POLICY_NAME,
                    policy_version=POLICY_VERSION,
                    inputs=inputs,
                    decision="CUSTO_POSITIVO_SEM_ORIGEM_DFE",
                    reasons=["Custo positivo exige origem DF-e"],
                    allowed=False,
                )
            if sale_price is not None and value > float(sale_price):
                return PolicyDecision(
                    policy_name=POLICY_NAME,
                    policy_version=POLICY_VERSION,
                    inputs=inputs,
                    decision="CUSTO_ACIMA_DA_VENDA",
                    confidence="HIGH",
                    reasons=["Custo DF-e e evidencia real e nao deve ser zerado"],
                    allowed=accept_negative_margin,
                    owner_risk_accepted=accept_negative_margin,
                    requires_review=True,
                    evidence_refs=["dfe_unit_cost"],
                )
            return PolicyDecision(
                policy_name=POLICY_NAME,
                policy_version=POLICY_VERSION,
                inputs=inputs,
                decision="CUSTO_DFE",
                confidence="HIGH",
                reasons=["Custo derivado de NF-e autorizada"],
                evidence_refs=["dfe_unit_cost"],
            )
        if cost_status != PENDING_COST_STATUS:
            return PolicyDecision(
                policy_name=POLICY_NAME,
                policy_version=POLICY_VERSION,
                inputs=inputs,
                decision="CUSTO_ZERO_SEM_STATUS_PENDENTE",
                reasons=["Custo zero exige cost_status=PENDING"],
                allowed=False,
            )
        if not allow_pending_dfe_cost:
            return PolicyDecision(
                policy_name=POLICY_NAME,
                policy_version=POLICY_VERSION,
                inputs=inputs,
                decision="CUSTO_ZERO_SEM_AUTORIZACAO_EXPLICITA",
                reasons=["Custo zero exige --allow-pending-dfe-cost no processo"],
                allowed=False,
            )
        return PolicyDecision(
            policy_name=POLICY_NAME,
            policy_version=POLICY_VERSION,
            inputs=inputs,
            decision="CUSTO_ZERO_AUTORIZADO",
            confidence="VERY_LOW",
            reasons=["Custo pendente autorizado explicitamente para este processo"],
            owner_risk_accepted=True,
            requires_review=True,
        )

    def sanitize_evidence(self, evidence: dict[str, Any] | None) -> dict[str, Any]:
        """Remove chave de acesso completa da NF-e."""
        if not evidence:
            return {}
        payload = dict(evidence)
        for key in ("access_key", "chaveAcesso", "accessKey"):
            if payload.get(key):
                payload[key] = _mask_access_key(str(payload[key]))
        if payload.get("accessKeyMasked"):
            payload["access_key"] = payload["accessKeyMasked"]
        return payload


def _mask_access_key(value: str) -> str:
    digits = "".join(c for c in value if c.isdigit())
    if len(digits) < 8:
        return "***"
    return f"{digits[:4]}***{digits[-4:]}"
