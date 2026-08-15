"""Politica de duplicidade: EAN e descricao, sem misturar variantes."""

from __future__ import annotations

from ..final_wave import (
    LEGITIMATE_VARIANT,
    SAME_PRODUCT,
    UNRESOLVED_DUPLICATE,
    classify_final_duplicate,
)
from .decision import PolicyDecision

POLICY_NAME = "duplicate_policy"
POLICY_VERSION = "1.0.0"


class DuplicatePolicy:
    """Classifica par candidato versus cadastro existente."""

    name = POLICY_NAME
    version = POLICY_VERSION

    def evaluate(
        self,
        candidate_description: str,
        existing_description: str,
        *,
        candidate_family: str | None = None,
        existing_family: str | None = None,
        existing_code: int | None = None,
    ) -> PolicyDecision:
        label, reason = classify_final_duplicate(
            candidate_description,
            existing_description,
            candidate_family=candidate_family,
            existing_family=existing_family,
        )
        allowed = label == LEGITIMATE_VARIANT
        return PolicyDecision(
            policy_name=POLICY_NAME,
            policy_version=POLICY_VERSION,
            inputs={
                "candidate_family": candidate_family,
                "existing_family": existing_family,
                "existing_code": existing_code,
            },
            decision=label,
            confidence="HIGH" if label != UNRESOLVED_DUPLICATE else "NONE",
            reasons=[reason],
            evidence_refs=[f"produtoCodigo:{existing_code}"] if existing_code else [],
            allowed=allowed,
            requires_review=label == UNRESOLVED_DUPLICATE,
        )

    def pre_post_action(self, decision: PolicyDecision) -> str:
        """Acao do executor: variante segue; o resto vira skip."""
        if decision.decision == SAME_PRODUCT:
            return "SKIPPED_PRE_POST_ALREADY_REGISTERED_BY_DESCRIPTION"
        if decision.decision == UNRESOLVED_DUPLICATE:
            return "SKIPPED_PRE_POST_UNRESOLVED_DUPLICATE"
        return "CONTINUE"
