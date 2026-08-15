"""Pontos de extensao futuros: interfaces e schemas, sem escrita e sem IA."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class CostUpdateCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ean: str
    produto_codigo: int | None = None
    custo_atual: float | None = None
    custo_proposto: float
    fonte: str = "DFE"


class CostUpdateProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate: CostUpdateCandidate
    variacao_percentual: float | None = None
    margem_resultante: float | None = None
    requer_aprovacao: bool = True


class CostUpdatePolicy(Protocol):
    def evaluate(self, proposal: CostUpdateProposal) -> dict[str, Any]: ...


class CostUpdateGateway(Protocol):
    def put_cost(self, proposal: CostUpdateProposal) -> dict[str, Any]: ...


class CostUpdateVerifier(Protocol):
    def verify(self, produto_codigo: int, expected_cost: float) -> dict[str, Any]: ...


class FiscalAuditInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ean: str
    ncm: str | None = None
    cest: str | None = None
    contexto_sanitizado: dict[str, Any] = Field(default_factory=dict)


class FiscalAuditFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str
    descricao: str
    impacto: str
    contestavel: bool = True


class FiscalAuditEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fonte: str
    vigencia: str | None = None
    referencia: str | None = None


class FiscalAuditRule(Protocol):
    def apply(self, payload: FiscalAuditInput) -> list[FiscalAuditFinding]: ...


class FiscalAuditRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding: FiscalAuditFinding
    acao: str
    confianca: str
    fontes: list[FiscalAuditEvidence] = Field(default_factory=list)
    requer_aprovacao: bool = True


class AiFiscalAdvisorPort(Protocol):
    """IA so analisa contexto sanitizado. Nao escreve e nao decide em silencio."""

    def recommend(self, payload: FiscalAuditInput) -> FiscalAuditRecommendation: ...
