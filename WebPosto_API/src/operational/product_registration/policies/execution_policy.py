"""Politica de execucao: skip pre-POST continua; falha pos-POST pode parar."""

from __future__ import annotations

from .decision import PolicyDecision

POLICY_NAME = "execution_policy"
POLICY_VERSION = "1.0.0"

CRITICAL_HALT = {
    "EMPRESA_DIVERGENTE",
    "SENTINEL_INDISPONIVEL",
    "HTTP_AUTH",
    "RET_REJEICAO",
    "RESULT_UNKNOWN",
    "DIVERGENCIA_POS_POST",
    "CHECKPOINT_PERSIST_FAIL",
}


class ExecutionPolicy:
    """Regras de lote comprovadas nas ondas 1-5."""

    name = POLICY_NAME
    version = POLICY_VERSION

    def should_create_lock(self, planned_posts: int) -> PolicyDecision:
        allowed = planned_posts > 0
        return PolicyDecision(
            policy_name=POLICY_NAME,
            policy_version=POLICY_VERSION,
            inputs={"planned_posts": planned_posts},
            decision="CREATE_LOCK" if allowed else "NO_LOCK_WITHOUT_POST",
            reasons=["Lock so existe quando ha POST previsto"] if not allowed else ["Lock autorizado"],
            allowed=allowed,
        )

    def on_pre_post_skip(self, reason: str) -> PolicyDecision:
        return PolicyDecision(
            policy_name=POLICY_NAME,
            policy_version=POLICY_VERSION,
            inputs={"reason": reason},
            decision="CONTINUE_BATCH",
            reasons=["SKIPPED_PRE_POST nao interrompe o lote"],
            allowed=True,
        )

    def on_post_outcome(self, classification: str) -> PolicyDecision:
        halt = classification in CRITICAL_HALT or classification.startswith("HTTP_AUTH")
        return PolicyDecision(
            policy_name=POLICY_NAME,
            policy_version=POLICY_VERSION,
            inputs={"classification": classification},
            decision="HALT_BATCH" if halt else "CONTINUE_BATCH",
            reasons=["Falha posterior ao POST interrompe"] if halt else ["Produto verificado"],
            allowed=not halt,
        )

    def timeout_requires_get(self) -> PolicyDecision:
        return PolicyDecision(
            policy_name=POLICY_NAME,
            policy_version=POLICY_VERSION,
            inputs={},
            decision="RESOLVE_TIMEOUT_BY_GET",
            reasons=["Timeout nunca autoriza reenvio cego; consultar EAN por GET"],
            allowed=True,
        )
