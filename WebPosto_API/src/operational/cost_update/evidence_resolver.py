"""Resolve evidencia de custo reutilizando DfeCostResolver. Sem recalcular a formula."""

from __future__ import annotations

from typing import Any

from src.operational.product_registration.dfe_cost_resolver import (
    STATUS_NOT_FOUND,
    STATUS_RESOLVED,
    STATUS_REVIEW_UNIT,
    CostEvidence,
    build_authorized_index,
    cost_from_index,
    evidence_to_dict,
    find_cost_evidence,
)
from src.operational.product_registration.policies.cost_policy import CostPolicy

EXPECTED_RECIPIENT = "02080237000155"


def digits_only(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


class CostEvidenceResolver:
    """EAN exato, destinatario 118508, NF-e autorizada mais recente."""

    def __init__(self, *, company_code: int = 118508, expected_recipient: str = EXPECTED_RECIPIENT) -> None:
        self.company_code = company_code
        self.expected_recipient = digits_only(expected_recipient)
        self._index: dict[str, tuple] | None = None
        self._sanitizer = CostPolicy()

    def build_index(self) -> dict[str, tuple]:
        self._index = build_authorized_index(self.company_code)
        return self._index

    def resolve(self, ean: str, *, use_index: bool = True) -> CostEvidence:
        if use_index:
            if self._index is None:
                self.build_index()
            evidence = cost_from_index(ean, self._index or {})
        else:
            evidence = find_cost_evidence(ean, self.company_code)
        return self._gate(evidence)

    def _gate(self, evidence: CostEvidence) -> CostEvidence:
        if evidence.status == STATUS_NOT_FOUND:
            return evidence
        recipient = digits_only(evidence.destinatario_cnpj)
        if recipient and recipient != self.expected_recipient:
            evidence.status = "BLOCKED_RECIPIENT_MISMATCH"
            evidence.reason = f"Destinatario {evidence.destinatario_cnpj} diverge de {self.expected_recipient}"
            return evidence
        if evidence.cancelada:
            evidence.status = "BLOCKED_CANCELLED"
            evidence.reason = "NF-e cancelada"
            return evidence
        if evidence.protocolo_cstat and evidence.protocolo_cstat != "100":
            evidence.status = "BLOCKED_NOT_AUTHORIZED"
            evidence.reason = f"cStat {evidence.protocolo_cstat}"
            return evidence
        if evidence.status == STATUS_REVIEW_UNIT or evidence.unidade_atomica is False:
            evidence.status = STATUS_REVIEW_UNIT
            return evidence
        if evidence.preco_custo is not None and evidence.preco_custo <= 0:
            evidence.status = "BLOCKED_NON_POSITIVE_COST"
            evidence.reason = "Custo calculado zero ou negativo"
            return evidence
        if evidence.match_type and evidence.match_type != "EXACT_EAN":
            evidence.status = "BLOCKED_EAN_MISMATCH"
            evidence.reason = f"Correspondencia {evidence.match_type} nao e EAN exato"
            return evidence
        if evidence.status == STATUS_RESOLVED and evidence.preco_custo is None:
            evidence.status = "BLOCKED_INCOMPLETE_CALCULATION"
            evidence.reason = "Calculo incompleto"
        return evidence

    def sanitize(self, evidence: CostEvidence) -> dict[str, Any]:
        payload = evidence_to_dict(evidence)
        payload.pop("access_key", None)
        return self._sanitizer.sanitize_evidence(payload)
