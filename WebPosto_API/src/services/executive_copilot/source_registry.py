"""Escopo, período SDS e gate de verdade do Copiloto. Sem rede e sem LLM."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

from src.core.management_scope import LICENSED_COMPANY_CODES
from src.services.complete_departmental_dre_service import CompleteDepartmentalDreService
from src.services.data_quality_provenance_service import DataQualityProvenanceService
from src.services.executive_copilot.contracts import (
    WEBPOSTO_WRITES,
    ClaimStatus,
    Confidence,
    ConfidenceLevel,
    CopilotAnswer,
    EvidenceItem,
    Impact,
    LineageItem,
    SpecialistId,
)
from src.services.sds_identity import LICENSED_SDS_CODES
from src.utils.filial_normalizer import EMPRESA_VIP, EMPRESA_VIP_LEGACY_ALIAS, resolve_empresa_codigo

BLOCKED_COMPANY = 118508
VIP_LEGACY_ALIAS = EMPRESA_VIP_LEGACY_ALIAS
FORBIDDEN_DEMO_CODES = frozenset({5333, 15880})
LICENSED_EXECUTIVE_UNITS = tuple(LICENSED_SDS_CODES)
DRE_DEPARTMENTS = CompleteDepartmentalDreService.DEPARTMENTS
MANUAL_EXPENSE_METHODS = frozenset({"MANUAL", "MANUAL_REVIEW"})
AUTO_EXPENSE_METHODS = frozenset({"KEYWORD", "RULE", "MODEL", "PATTERN", "FUZZY"})


class CompleteSdsDateProvider(Protocol):
    """Última data SDS completa já comprovada localmente. Sem I/O remoto."""

    def last_complete_date(self) -> date | None: ...


class StaticCompleteSdsDateProvider:
    """Provider injetável. `None` = sem completude comprovada."""

    def __init__(self, complete_on: date | None) -> None:
        self._complete_on = complete_on

    def last_complete_date(self) -> date | None:
        return self._complete_on


@dataclass(frozen=True)
class UnitResolution:
    units: list[int]
    persisted_units: list[int]
    blocked: dict[str, str] | None
    normalized_alias: bool = False


def resolve_executive_units(raw_codes: list[int] | tuple[int, ...] | None) -> UnitResolution:
    """Resolve unidades do Copiloto. 6666 vira 11495 e nunca é persistido."""
    if not raw_codes:
        licensed = list(LICENSED_EXECUTIVE_UNITS)
        return UnitResolution(units=licensed, persisted_units=list(licensed), blocked=None)

    units: list[int] = []
    normalized_alias = False
    for raw in raw_codes:
        try:
            code = int(raw)
        except (TypeError, ValueError):
            return UnitResolution(
                units=[],
                persisted_units=[],
                blocked={"code": "UNIT_INVALID", "message": "Unidade inválida."},
            )
        if code == BLOCKED_COMPANY:
            return UnitResolution(
                units=[],
                persisted_units=[],
                blocked={"code": "UNIT_BLOCKED", "message": "118508 bloqueado neste Copiloto Executivo."},
            )
        if code in FORBIDDEN_DEMO_CODES:
            return UnitResolution(
                units=[],
                persisted_units=[],
                blocked={"code": "UNIT_FORBIDDEN", "message": f"Unidade {code} não faz parte do escopo executivo."},
            )
        if code == VIP_LEGACY_ALIAS:
            code = EMPRESA_VIP
            normalized_alias = True
        else:
            resolved = resolve_empresa_codigo(code)
            if resolved == VIP_LEGACY_ALIAS:
                code = EMPRESA_VIP
                normalized_alias = True
            elif resolved in LICENSED_COMPANY_CODES:
                code = int(resolved)
            elif code not in LICENSED_COMPANY_CODES:
                return UnitResolution(
                    units=[],
                    persisted_units=[],
                    blocked={"code": "UNIT_OUT_OF_SCOPE", "message": f"Unidade {code} fora do escopo 5555/11495/74014."},
                )
        if code not in LICENSED_SDS_CODES:
            return UnitResolution(
                units=[],
                persisted_units=[],
                blocked={"code": "UNIT_OUT_OF_SCOPE", "message": f"Unidade {code} fora do escopo SDS."},
            )
        if code not in units:
            units.append(code)

    persisted = [code for code in units if code != VIP_LEGACY_ALIAS]
    return UnitResolution(
        units=persisted,
        persisted_units=list(persisted),
        blocked=None,
        normalized_alias=normalized_alias,
    )


def dre_numeric_status(line: dict[str, Any], *, homologated: bool) -> ClaimStatus:
    """Lê a linha da DRE departamental. Sem CMV ou sem homologação não vira FACT."""
    missing = [str(item) for item in (line.get("missingEvidence") or [])]
    cost = line.get("cost")
    if line.get("status") == "BLOQUEADO" or "CUSTO" in missing or cost in (None, ""):
        return ClaimStatus.BLOCKED if line.get("status") == "BLOQUEADO" else ClaimStatus.UNAVAILABLE
    if not homologated:
        return ClaimStatus.UNAVAILABLE
    return ClaimStatus.FACT


def _as_items(kind: type[EvidenceItem] | type[LineageItem], rows: list[Any]) -> list[Any]:
    parsed: list[Any] = []
    for row in rows:
        if isinstance(row, kind):
            parsed.append(row)
        else:
            parsed.append(kind.model_validate(row))
    return parsed


class TruthGate:
    """Aplica estados canônicos. Não consulta WebPosto e não inventa lucro."""

    def __init__(
        self,
        provenance: DataQualityProvenanceService | None = None,
        sds_complete_provider: CompleteSdsDateProvider | None = None,
    ) -> None:
        self._provenance = provenance or DataQualityProvenanceService()
        self._sds_complete = sds_complete_provider

    def last_complete_date(self) -> date | None:
        if self._sds_complete is None:
            return None
        return self._sds_complete.last_complete_date()

    def period_status(self, day: date) -> ClaimStatus:
        complete = self.last_complete_date()
        if complete is None or day > complete:
            return ClaimStatus.BLOCKED
        return ClaimStatus.FACT

    def simulation_status(self) -> ClaimStatus:
        return ClaimStatus.ESTIMATED

    def expense_claim_status(self, *, method: str | None, homologated: bool) -> ClaimStatus:
        normalized = str(method or "").strip().upper()
        if not normalized:
            return ClaimStatus.UNAVAILABLE
        if normalized in MANUAL_EXPENSE_METHODS:
            return ClaimStatus.FACT if homologated else ClaimStatus.UNAVAILABLE
        if normalized in AUTO_EXPENSE_METHODS:
            return ClaimStatus.AUTO_CLASSIFIED
        return ClaimStatus.UNAVAILABLE

    def profit_impact(
        self,
        *,
        revenue: float | None,
        cmv: float | None,
        evidence: list[Any],
        lineage: list[Any],
    ) -> Impact:
        del revenue
        proven = self._provenance.evaluate(
            {
                "title": "lucro líquido",
                "claims": ["lucro_liquido"],
                "evidence": {"cmv": cmv, "sourceEndpoints": ["ABASTECIMENTO"] if evidence else []},
                "confidence": 0.0,
            }
        )
        if cmv is None or proven.get("factClassification") in {"INDISPONIVEL", "ESTIMATIVA"}:
            return Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE)
        if not evidence or not lineage:
            return Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE)
        return Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE)

    def economy_impact(
        self,
        *,
        amount: float | None,
        evidence: list[Any],
        lineage: list[Any],
    ) -> Impact:
        if not evidence or not lineage:
            return Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE)
        return Impact(amount=amount, currency="BRL", status=ClaimStatus.ESTIMATED)

    def confidence_for(self, status: ClaimStatus) -> Confidence:
        if status == ClaimStatus.FACT:
            return Confidence(score=0.8, level=ConfidenceLevel.ALTA, reasons=[])
        if status == ClaimStatus.ESTIMATED:
            return Confidence(score=0.45, level=ConfidenceLevel.MEDIA, reasons=[f"claim={status}"])
        if status == ClaimStatus.AUTO_CLASSIFIED:
            return Confidence(score=0.4, level=ConfidenceLevel.MEDIA, reasons=[f"claim={status}"])
        return Confidence(score=0.1, level=ConfidenceLevel.BAIXA, reasons=[f"claim={status}"])

    def blocked_answer(
        self,
        *,
        specialist: SpecialistId,
        question: str,
        reason: str,
        code: str,
    ) -> CopilotAnswer:
        del question
        return CopilotAnswer(
            specialist=specialist,
            answer=reason,
            fact="",
            inference="",
            recommendation="",
            impact=Impact(amount=None, currency="BRL", status=ClaimStatus.BLOCKED),
            blocked={"code": code, "message": reason},
            confidence=self.confidence_for(ClaimStatus.BLOCKED),
            webpostoWrites=WEBPOSTO_WRITES,
        )

    def build_answer(
        self,
        *,
        specialist: SpecialistId,
        question: str,
        fact: str = "",
        inference: str = "",
        recommendation: str = "",
        impact: Impact | None = None,
        units: list[int] | None = None,
        departments: list[str] | None = None,
        probable_cause: str | None = None,
        evidence: list[Any] | None = None,
        lineage: list[Any] | None = None,
        simulation: dict[str, Any] | None = None,
        suggested_action: dict[str, Any] | None = None,
        period_end: date | None = None,
        confidence: Confidence | None = None,
    ) -> CopilotAnswer:
        del question
        resolved = resolve_executive_units(units)
        if resolved.blocked:
            return self.blocked_answer(
                specialist=specialist,
                question="",
                reason=resolved.blocked["message"],
                code=resolved.blocked["code"],
            )
        status_impact = impact or Impact(amount=None, currency="BRL", status=ClaimStatus.UNAVAILABLE)
        complete = self.last_complete_date()
        if period_end is not None and self.period_status(period_end) == ClaimStatus.BLOCKED:
            if complete is None:
                reason = "Nenhuma data SDS completa comprovada."
            else:
                reason = f"Período posterior a {complete.isoformat()} sem catch-up autorizado."
            return self.blocked_answer(
                specialist=specialist,
                question="",
                reason=reason,
                code="PERIOD_BLOCKED",
            )
        if simulation is not None and status_impact.status != ClaimStatus.ESTIMATED:
            status_impact = status_impact.model_copy(update={"status": ClaimStatus.ESTIMATED})
        typed_evidence = _as_items(EvidenceItem, list(evidence or []))
        typed_lineage = _as_items(LineageItem, list(lineage or []))
        if complete is not None:
            typed_lineage = [
                item.model_copy(update={"sds_complete_as_of": item.sds_complete_as_of or complete})
                for item in typed_lineage
            ]
        if status_impact.status == ClaimStatus.FACT and (not typed_evidence or not typed_lineage):
            raise ValueError("FACT exige evidência e linhagem")
        return CopilotAnswer(
            specialist=specialist,
            answer=fact or inference or recommendation,
            fact=fact,
            inference=inference,
            recommendation=recommendation,
            impact=status_impact,
            units=resolved.persisted_units,
            departments=[d for d in (departments or []) if d in DRE_DEPARTMENTS],
            probableCause=probable_cause,
            evidence=typed_evidence,
            lineage=typed_lineage,
            confidence=confidence or self.confidence_for(status_impact.status),
            simulation=simulation,
            suggestedAction=suggested_action,
            webpostoWrites=WEBPOSTO_WRITES,
        )
