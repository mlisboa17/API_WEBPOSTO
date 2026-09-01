"""Contratos publicos do motor de proposta de custo."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .versions import CANDIDATE_SCHEMA_VERSION, PROPOSAL_SCHEMA_VERSION

ProposalStatus = Literal[
    "PROPOSED",
    "NO_CHANGE",
    "REVIEW_REQUIRED",
    "BLOCKED",
    "DFE_NOT_FOUND",
]


class CostUpdateCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = CANDIDATE_SCHEMA_VERSION
    empresa_codigo: int
    produto_codigo: int | None = None
    ean: str
    descricao: str | None = None
    custo_atual: Decimal | None = None
    preco_venda: Decimal | None = None
    ncm: str | None = None
    cest: str | None = None
    evidencia_dfe: dict[str, Any] = Field(default_factory=dict)
    origem: str = "pending_cost_update"


class CurrentProductState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    ambiguous: bool = False
    empresa_codigo: int | None = None
    produto_codigo: int | None = None
    ean_confirmado: bool = False
    ativo: bool | None = None
    custo_atual: Decimal | None = None
    preco_venda: Decimal | None = None
    ncm: str | None = None
    cest: str | None = None
    descricao: str | None = None
    classification: str = "OK"
    reasons: list[str] = Field(default_factory=list)
    api_reads: int = 0


class CostUpdateProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PROPOSAL_SCHEMA_VERSION
    proposal_id: str
    proposal_hash: str
    version: int = 1
    status: ProposalStatus
    empresa_codigo: int
    produto_codigo: int | None = None
    ean: str
    descricao: str | None = None
    custo_anterior: Decimal | None = None
    custo_proposto: Decimal | None = None
    diferenca_absoluta: Decimal | None = None
    variacao_percentual: Decimal | None = None
    preco_venda: Decimal | None = None
    markup_anterior: Decimal | None = None
    markup_projetado: Decimal | None = None
    margem_anterior: Decimal | None = None
    margem_projetada: Decimal | None = None
    lucro_unitario_estimado: Decimal | None = None
    custo_acima_da_venda: bool = False
    nfe: dict[str, Any] = Field(default_factory=dict)
    formula: str | None = None
    confianca: str = "NONE"
    riscos: list[str] = Field(default_factory=list)
    policy_version: str
    created_at: str
    updated_at: str
    previous_proposal_hash: str | None = None
    lifecycle: str = "ACTIVE"


class ScanSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    empresa_codigo: int
    analyzed: int = 0
    located_on_webposto: int = 0
    linked_to_company: int = 0
    with_valid_dfe: int = 0
    still_zero_cost: int = 0
    api_reads: int = 0
    api_writes: int = 0
    sources: dict[str, int] = Field(default_factory=dict)
    items: list[dict[str, Any]] = Field(default_factory=list)
