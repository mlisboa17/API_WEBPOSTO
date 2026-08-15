"""Politica versionada de classificacao de propostas de custo."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.operational.product_registration.dfe_cost_resolver import (
    STATUS_NOT_FOUND,
    STATUS_RESOLVED,
    STATUS_REVIEW_UNIT,
    CostEvidence,
)

from .decimal_utils import ratio, to_decimal
from .schemas import CurrentProductState
from .versions import POLICY_NAME, POLICY_VERSION

ABS_TOLERANCE = Decimal("0.01")
PCT_TOLERANCE = Decimal("0")
MAX_INCREASE = Decimal("0.30")
MAX_DECREASE = Decimal("0.30")
MIN_MARGIN = Decimal("0")


class CostUpdateProposalPolicy:
    name = POLICY_NAME
    version = POLICY_VERSION

    def __init__(
        self,
        *,
        abs_tolerance: Decimal = ABS_TOLERANCE,
        pct_tolerance: Decimal = PCT_TOLERANCE,
        max_increase: Decimal = MAX_INCREASE,
        max_decrease: Decimal = MAX_DECREASE,
        min_margin: Decimal = MIN_MARGIN,
        allow_inactive: bool = False,
    ) -> None:
        self.abs_tolerance = abs_tolerance
        self.pct_tolerance = pct_tolerance
        self.max_increase = max_increase
        self.max_decrease = max_decrease
        self.min_margin = min_margin
        self.allow_inactive = allow_inactive

    def classify(
        self,
        *,
        current: CurrentProductState,
        evidence: CostEvidence,
        expected_ean: str,
        expected_ncm: str | None = None,
        expected_cest: str | None = None,
    ) -> dict[str, Any]:
        riscos: list[str] = []
        if current.classification == "BLOCKED_WRONG_COMPANY" or (
            current.empresa_codigo and current.empresa_codigo != 118508
        ):
            return self._decision("BLOCKED", ["produto nao esta na empresa 118508"], "HIGH")
        if current.ambiguous or current.classification == "BLOCKED_AMBIGUOUS_GET":
            return self._decision("BLOCKED", ["resposta GET ambigua"], "HIGH")
        if not current.ean_confirmado or current.classification == "BLOCKED_EAN_MISMATCH":
            return self._decision("BLOCKED", ["EAN diverge"], "HIGH")
        if current.ativo is False and not self.allow_inactive:
            return self._decision("BLOCKED", ["produto inativo"], "HIGH")
        if evidence.status == STATUS_NOT_FOUND:
            return self._decision("DFE_NOT_FOUND", ["nenhum DF-e valido pelo EAN exato"], "NONE")
        if evidence.status in {"BLOCKED_RECIPIENT_MISMATCH", "BLOCKED_CANCELLED", "BLOCKED_NOT_AUTHORIZED"}:
            return self._decision("BLOCKED", [evidence.reason or evidence.status], "HIGH")
        if evidence.status in {"BLOCKED_NON_POSITIVE_COST", "BLOCKED_INCOMPLETE_CALCULATION", "BLOCKED_EAN_MISMATCH"}:
            return self._decision("BLOCKED", [evidence.reason or evidence.status], "HIGH")
        if evidence.status == STATUS_REVIEW_UNIT or evidence.unidade_atomica is False:
            return self._decision(
                "REVIEW_REQUIRED",
                [evidence.reason or "conversao de embalagem indeterminavel"],
                "LOW",
            )
        if evidence.status != STATUS_RESOLVED or evidence.preco_custo is None:
            return self._decision("BLOCKED", [evidence.reason or "calculo incompleto"], "HIGH")

        proposed = to_decimal(evidence.preco_custo)
        if proposed <= 0:
            return self._decision("BLOCKED", ["custo zero ou negativo"], "HIGH")

        current_cost = to_decimal(current.custo_atual)
        sale = to_decimal(current.preco_venda)
        delta = proposed - current_cost
        pct = None if current_cost <= 0 else ratio(delta, current_cost)
        if current_cost > 0 and abs(delta) < self.abs_tolerance:
            return self._decision("NO_CHANGE", ["diferenca absoluta inferior a 0.01"], "HIGH")
        if pct is not None and abs(pct) <= self.pct_tolerance and self.pct_tolerance > 0:
            return self._decision("NO_CHANGE", ["variacao dentro da tolerancia"], "HIGH")
        if current_cost == 0 and proposed == 0:
            return self._decision("NO_CHANGE", ["ambos os custos sao zero"], "LOW")

        if sale > 0 and proposed > sale:
            riscos.append("custo proposto acima do preco de venda")
        margem = ratio(sale - proposed, sale) if sale > 0 else None
        if margem is not None and margem < 0:
            riscos.append("margem projetada negativa")
        elif margem is not None and margem < self.min_margin:
            riscos.append("margem projetada abaixo do limite")
        if current_cost > 0 and pct is not None and pct > self.max_increase:
            riscos.append("aumento superior a 30%")
        if current_cost > 0 and pct is not None and pct < -self.max_decrease:
            riscos.append("reducao superior a 30%")
        if evidence.quantidade_origem == "uTrib":
            riscos.append("conversao incomum via qTrib")
        if expected_ncm and evidence.item_ncm and str(expected_ncm) != str(evidence.item_ncm):
            riscos.append("conflito NCM")
        if expected_cest and evidence.item_cest and str(expected_cest) != str(evidence.item_cest):
            riscos.append("conflito CEST")
        if evidence.candidatos_avaliados > 1:
            riscos.append("multiplos itens plausiveis")
        if (
            evidence.unidade_comercial
            and evidence.quantidade_origem == "uTrib"
        ):
            riscos.append("divergencia entre unidade comercial e tributavel")

        if riscos:
            return self._decision("REVIEW_REQUIRED", riscos, "MEDIUM")
        return self._decision("PROPOSED", [], "HIGH")

    def _decision(self, status: str, riscos: list[str], confianca: str) -> dict[str, Any]:
        return {
            "policy_name": self.name,
            "policy_version": self.version,
            "status": status,
            "riscos": riscos,
            "confianca": confianca,
        }
