"""DIR-01 — modelos de evidence_items para decisões."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NominalEvidenceItem(BaseModel):
    """Linha nominal extraída de fonte complementar (ex.: Prestação de Contas)."""

    source: str
    source_file: str | None = None
    empresa_codigo: str | None = None
    tenant_id: str | None = None
    tenant_name: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    cash_register: str | None = None
    shift: str | None = None
    date: str | None = None
    financial_nature: str | None = None
    capture_origin: str | None = None
    person_name: str | None = None
    funcionario_codigo: int | None = None
    amount: float
    raw_amount: float | None = None
    description: str | None = None
    document_reference: str | None = None
    raw_text: str | None = None
    page_number: int | None = None
    line_reference: str | None = None
    extraction_confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BeneficiaryVsReview(BaseModel):
    beneficiary_available: bool = False
    review_responsible: str | None = None
    review_workflow_implemented: bool = False


class DecisionEvidenceItem(BaseModel):
    id: str
    tenant_id: str
    empresa_codigo: str | None = None
    tenant_name: str | None = None
    source: str
    category: str | None = None
    person_name: str | None = None
    funcionario_codigo: int | None = None
    date: str | None = None
    amount: float
    description: str | None = None
    origin: str | None = None
    cash_register: str | None = None
    shift: str | None = None
    document_reference: str | None = None
    status: str | None = None
    match_status: str | None = None
    match_confidence: float | None = None
    nominal_source: str | None = None
    nominal_source_file: str | None = None
    nominal_source_page: int | None = None
    nominal_source_reference: str | None = None
    matching_reason: str | None = None
    beneficiary_vs_review: BeneficiaryVsReview | None = None
    limitations: list[str] = Field(default_factory=list)
    review_responsible: str | None = None
    raw_reference: dict[str, Any] = Field(default_factory=dict)


class DecisionEvidenceResponse(BaseModel):
    decision_id: str
    decision_summary: str
    root_cause: str | None = None
    money_found: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None
    evidence_items: list[DecisionEvidenceItem] = Field(default_factory=list)
    evidence_items_count: int = 0
    evidence_items_total: float = 0.0
    limitations: list[str] = Field(default_factory=list)
    source_metadata: dict[str, Any] = Field(default_factory=dict)
