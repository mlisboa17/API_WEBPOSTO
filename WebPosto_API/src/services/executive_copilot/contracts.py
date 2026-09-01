"""Contrato canônico da resposta do Copiloto Executivo. Sem I/O e sem LLM."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.services.executive_copilot.unit_capabilities import (
    COPILOT_UNIT_CODES,
    PISTA_UNIT_CODES,
    VIP_ALIAS,
)
from src.services.sds_sanitize import sanitize_value

WEBPOSTO_WRITES = 0
LICENSED_PUBLIC_UNITS = frozenset(COPILOT_UNIT_CODES)
FORBIDDEN_PUBLIC_UNITS = frozenset({VIP_ALIAS, 5333, 15880})
LICENSED_PISTA_UNITS = frozenset(PISTA_UNIT_CODES)

SpecialistId = Literal["PRESIDENTE", "FINANCEIRO", "OPERACIONAL"]


class ClaimStatus(StrEnum):
    FACT = "FACT"
    ESTIMATED = "ESTIMATED"
    AUTO_CLASSIFIED = "AUTO_CLASSIFIED"
    UNAVAILABLE = "UNAVAILABLE"
    BLOCKED = "BLOCKED"


class ConfidenceLevel(StrEnum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"


class SourceNature(StrEnum):
    LOCAL = "LOCAL"
    LOCAL_HOMOLOGATED = "LOCAL_HOMOLOGATED"
    SNAPSHOT = "SNAPSHOT"
    CHECKPOINT = "CHECKPOINT"


class Impact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: float | None = None
    currency: str = "BRL"
    status: ClaimStatus

    @model_validator(mode="after")
    def _clear_amount_when_unpublished(self) -> Impact:
        if self.status in {ClaimStatus.UNAVAILABLE, ClaimStatus.BLOCKED}:
            self.amount = None
        return self


class Confidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float
    level: ConfidenceLevel
    reasons: list[str] = Field(default_factory=list)

    @field_validator("score")
    @classmethod
    def _score_unit_interval(cls, value: float) -> float:
        score = float(value)
        if score < 0.0 or score > 1.0:
            raise ValueError("confidence.score deve estar entre 0 e 1")
        return score


class BlockedInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class PeriodWindow(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    start: date = Field(alias="inicio")
    end: date = Field(alias="fim")

    @field_validator("start", "end", mode="before")
    @classmethod
    def _parse_day(cls, value: Any) -> date:
        if isinstance(value, date):
            return value
        text = str(value or "").strip()
        if not text:
            raise ValueError("período vazio")
        return date.fromisoformat(text)

    @model_validator(mode="after")
    def _start_not_after_end(self) -> PeriodWindow:
        if self.start > self.end:
            raise ValueError("inicio deve ser menor ou igual a fim")
        return self


def _licensed_unit(value: Any) -> int | None:
    if value is None or value == "":
        return None
    code = int(value)
    if code in FORBIDDEN_PUBLIC_UNITS or code not in LICENSED_PUBLIC_UNITS:
        raise ValueError(f"unidade {code} não é publicável no Copiloto")
    return code


class EvidenceItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str
    source: str = Field(alias="fonte")
    summary: str = Field(alias="resumo")
    claim_status: ClaimStatus = Field(alias="claimStatus")
    period: PeriodWindow | None = Field(None, alias="periodo")
    reference_date: date | None = Field(None, alias="dataReferencia")
    empresa_codigo: int | None = Field(None, alias="empresaCodigo")
    consolidated_scope: bool = Field(False, alias="escopoConsolidado")

    @field_validator("id", "source", "summary")
    @classmethod
    def _required_text(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("campo obrigatório vazio")
        return text

    @field_validator("empresa_codigo")
    @classmethod
    def _unit_if_present(cls, value: int | None) -> int | None:
        return _licensed_unit(value)

    @field_validator("reference_date", mode="before")
    @classmethod
    def _parse_ref(cls, value: Any) -> date | None:
        if value in (None, ""):
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    @model_validator(mode="after")
    def _require_period_and_scope(self) -> EvidenceItem:
        if self.period is None and self.reference_date is None:
            raise ValueError("evidência FACT exige período ou dataReferencia")
        if self.empresa_codigo is None and not self.consolidated_scope:
            raise ValueError("evidência exige unidade ou escopoConsolidado")
        return self


class LineageItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    origin: str = Field(alias="origem")
    source: str = Field(alias="fonte")
    period: PeriodWindow = Field(alias="periodo")
    reference: str = Field(alias="referencia")
    source_nature: SourceNature = Field(alias="naturezaFonte")
    local_source: bool = Field(True, alias="fonteLocal")
    empresa_codigo: int | None = Field(None, alias="empresaCodigo")
    consolidated_scope: bool = Field(False, alias="escopoConsolidado")
    sds_complete_as_of: date | None = Field(None, alias="sdsCompletoAte")

    @field_validator("origin", "source", "reference")
    @classmethod
    def _required_text(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("campo obrigatório vazio")
        return text

    @field_validator("empresa_codigo")
    @classmethod
    def _unit_if_present(cls, value: int | None) -> int | None:
        return _licensed_unit(value)

    @field_validator("sds_complete_as_of", mode="before")
    @classmethod
    def _parse_complete(cls, value: Any) -> date | None:
        if value in (None, ""):
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    @model_validator(mode="after")
    def _require_scope(self) -> LineageItem:
        if self.empresa_codigo is None and not self.consolidated_scope:
            raise ValueError("linhagem exige unidade ou escopoConsolidado")
        self.local_source = self.source_nature in {
            SourceNature.LOCAL,
            SourceNature.LOCAL_HOMOLOGATED,
            SourceNature.SNAPSHOT,
            SourceNature.CHECKPOINT,
        }
        return self


class CopilotAnswer(BaseModel):
    """Resposta executiva: fato, inferência e recomendação nunca se misturam."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    specialist: SpecialistId
    answer: str = ""
    fact: str = ""
    inference: str = ""
    recommendation: str = ""
    impact: Impact
    units: list[int] = Field(default_factory=list)
    unit_public_names: list[str] = Field(default_factory=list, alias="unitPublicNames")
    departments: list[str] = Field(default_factory=list)
    probable_cause: str | None = Field(None, alias="probableCause")
    evidence: list[EvidenceItem] = Field(default_factory=list)
    lineage: list[LineageItem] = Field(default_factory=list)
    confidence: Confidence = Field(
        default_factory=lambda: Confidence(score=0.0, level=ConfidenceLevel.BAIXA)
    )
    simulation: dict[str, Any] | None = None
    suggested_action: dict[str, Any] | None = Field(None, alias="suggestedAction")
    blocked: BlockedInfo | None = None
    webposto_writes: int = Field(WEBPOSTO_WRITES, alias="webpostoWrites")
    consolidated_scope: bool = Field(False, alias="consolidatedScope")

    @field_validator("blocked", mode="before")
    @classmethod
    def _coerce_blocked(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return BlockedInfo.model_validate(value)
        return value

    @field_validator("units")
    @classmethod
    def _only_licensed_units(cls, value: list[int]) -> list[int]:
        cleaned: list[int] = []
        for raw in value:
            code = int(raw)
            if code in FORBIDDEN_PUBLIC_UNITS or code not in LICENSED_PUBLIC_UNITS:
                raise ValueError(f"unidade {code} rejeitada no contrato público")
            if code not in cleaned:
                cleaned.append(code)
        return cleaned

    @model_validator(mode="after")
    def _enforce_truth(self) -> CopilotAnswer:
        self.webposto_writes = WEBPOSTO_WRITES
        if self.simulation is not None and self.impact.status != ClaimStatus.ESTIMATED:
            self.impact = self.impact.model_copy(update={"status": ClaimStatus.ESTIMATED})
        if not self.units and (self.blocked is None or self.impact.status != ClaimStatus.BLOCKED):
            raise ValueError("units vazias só são permitidas em resposta BLOCKED")
        if self.impact.status == ClaimStatus.FACT:
            if not self.evidence or not self.lineage:
                raise ValueError("FACT exige evidência e linhagem")
            if any(item.claim_status != ClaimStatus.FACT for item in self.evidence):
                raise ValueError("FACT exige evidências com claimStatus=FACT")
            _require_fact_unit_coherence(self)
            _require_fact_lineage_nature(self)
        if self.impact.status in {ClaimStatus.UNAVAILABLE, ClaimStatus.BLOCKED}:
            self.impact = Impact(
                amount=None,
                currency=self.impact.currency,
                status=self.impact.status,
            )
        self.confidence = _coherent_confidence(self.impact.status, self.confidence)
        if self.units:
            from src.services.executive_copilot.unit_capabilities import public_names

            self.unit_public_names = public_names(self.units)
        else:
            self.unit_public_names = []
        return self

    def to_public_payload(self) -> dict[str, Any]:
        raw = self.model_dump(mode="json", by_alias=True, exclude_none=False)
        raw["webpostoWrites"] = WEBPOSTO_WRITES
        return sanitize_value(raw)


FACT_SUSTAINING_NATURES = frozenset(
    {SourceNature.CHECKPOINT, SourceNature.LOCAL, SourceNature.LOCAL_HOMOLOGATED}
)
_F053_MARKERS = ("f05.3", "f053", "5333", "15880")


def _legacy_f053(item: LineageItem) -> bool:
    blob = f"{item.origin} {item.source} {item.reference}".lower()
    return any(marker in blob for marker in _F053_MARKERS)


def _item_matches_answer_units(
    *,
    empresa_codigo: int | None,
    consolidated: bool,
    answer_units: list[int],
) -> None:
    official = set(LICENSED_PISTA_UNITS)
    units = set(answer_units)
    if consolidated:
        if units != official:
            raise ValueError("escopo consolidado exige as três pistas oficiais")
        return
    if empresa_codigo is None or empresa_codigo not in units:
        raise ValueError("evidência/linhagem fora das unidades da resposta")


def _require_fact_unit_coherence(answer: CopilotAnswer) -> None:
    for item in answer.evidence:
        _item_matches_answer_units(
            empresa_codigo=item.empresa_codigo,
            consolidated=item.consolidated_scope,
            answer_units=answer.units,
        )
    for item in answer.lineage:
        _item_matches_answer_units(
            empresa_codigo=item.empresa_codigo,
            consolidated=item.consolidated_scope,
            answer_units=answer.units,
        )


def _require_fact_lineage_nature(answer: CopilotAnswer) -> None:
    if any(_legacy_f053(item) for item in answer.lineage):
        raise ValueError("snapshot F05.3 não sustenta FACT")
    if not any(item.source_nature in FACT_SUSTAINING_NATURES for item in answer.lineage):
        raise ValueError("FACT exige linhagem CHECKPOINT, LOCAL ou LOCAL_HOMOLOGATED")


def _coherent_confidence(status: ClaimStatus, confidence: Confidence) -> Confidence:
    if status in {ClaimStatus.BLOCKED, ClaimStatus.UNAVAILABLE, ClaimStatus.AUTO_CLASSIFIED}:
        if confidence.level == ConfidenceLevel.ALTA or confidence.score >= 0.75:
            return Confidence(
                score=min(confidence.score, 0.49),
                level=ConfidenceLevel.BAIXA if status != ClaimStatus.AUTO_CLASSIFIED else ConfidenceLevel.MEDIA,
                reasons=[*confidence.reasons, f"level limitado para {status}"],
            )
    return confidence
