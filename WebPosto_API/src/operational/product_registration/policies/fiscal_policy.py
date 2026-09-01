"""Politica fiscal: evidencia primeiro; vazio nao e zero; NCM nao elege CST."""

from __future__ import annotations

from typing import Any

from ..fiscal_resolver import ST_ABSENT, ST_ANTICIPATION_POSSIBLE, ST_NO_EVIDENCE, ST_PROVEN
from .decision import PolicyDecision

POLICY_NAME = "fiscal_policy"
POLICY_VERSION = "1.0.0"


class FiscalPolicy:
    """Decide se ha payload fiscal deterministico e com qual confianca."""

    name = POLICY_NAME
    version = POLICY_VERSION

    def evaluate_entry_classification(self, classification: str) -> PolicyDecision:
        mapping = {
            ST_PROVEN: ("ST_COMPROVADA", "HIGH", True, False),
            ST_ABSENT: ("SEM_ST_COMPROVADA", "LOW", True, True),
            ST_ANTICIPATION_POSSIBLE: ("ANTECIPACAO_POSSIVEL", "LOW", True, True),
            ST_NO_EVIDENCE: ("SEM_EVIDENCIA_DE_ENTRADA", "VERY_LOW", False, True),
        }
        decision, confidence, allowed, review = mapping.get(
            classification, ("EVIDENCIA_INDEFINIDA", "NONE", False, True)
        )
        return PolicyDecision(
            policy_name=POLICY_NAME,
            policy_version=POLICY_VERSION,
            inputs={"classification": classification},
            decision=decision,
            confidence=confidence,
            reasons=[f"Classificacao de entrada: {classification}"],
            allowed=allowed,
            requires_review=review,
            owner_risk_accepted=confidence != "HIGH",
        )

    def reject_ncm_prefix_as_cst(self, ncm: str | None, cst: str | None) -> PolicyDecision:
        """Prefixo de NCM nunca autoriza CST 060 a partir de CST 00."""
        return PolicyDecision(
            policy_name=POLICY_NAME,
            policy_version=POLICY_VERSION,
            inputs={"ncm": ncm, "cst": cst},
            decision="NCM_PREFIX_NOT_A_TAX_BASIS",
            reasons=["Prefixo de NCM nao elege tratamento tributario"],
            allowed=False,
        )

    def empty_is_not_zero(self, field: str, value: Any) -> PolicyDecision:
        missing = value is None or (isinstance(value, str) and value.strip() == "")
        return PolicyDecision(
            policy_name=POLICY_NAME,
            policy_version=POLICY_VERSION,
            inputs={"field": field, "declared": not missing},
            decision="FIELD_MISSING" if missing else "FIELD_DECLARED",
            reasons=["Campo vazio nao pode ser tratado como zero"] if missing else ["Campo declarado"],
            allowed=not missing,
        )

    def accept_owner_inference(
        self,
        *,
        selection_reason: str,
        alternatives: list[dict[str, Any]] | None = None,
        accept_fiscal_risk: bool,
    ) -> PolicyDecision:
        return PolicyDecision(
            policy_name=POLICY_NAME,
            policy_version=POLICY_VERSION,
            inputs={
                "selection_reason": selection_reason,
                "alternatives": alternatives or [],
                "accept_fiscal_risk": accept_fiscal_risk,
            },
            decision=selection_reason,
            confidence="VERY_LOW",
            reasons=["Inferencia fiscal com risco assumido pelo proprietario"],
            allowed=accept_fiscal_risk,
            owner_risk_accepted=accept_fiscal_risk,
            requires_review=True,
        )
