"""Schemas Pydantic para cadastro de produtos — FASES 3-10."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ProductStatus = Literal[
    "READY_TO_CREATE",
    "BLOCKED",
    "REVIEW_REQUIRED",
    "CREATED_AND_VERIFIED",
    "CREATED_BUT_NOT_VERIFIED",
    "REJECTED",
    "RESULT_UNKNOWN",
]

RiskLevel = Literal["BAIXO_RISCO", "MÉDIO_RISCO", "ALTO_RISCO"]


class ProductRow(BaseModel):
    """Linha da planilha mapeada (FASE 3)."""

    model_config = ConfigDict(extra="allow")

    linha_origem: int
    ean: str
    descricao: str
    preco_venda: float
    empresa_codigo: int
    empresa_nome: str
    grupo_api_codigo: int | None = None
    centro_api_codigo: int | None = None
    preco_compra: float | None = None
    preco_custo: float | None = None
    ncm: str | None = None
    cest: str | None = None
    cfop_entrada: str | None = None
    cfop_saida: str | None = None
    iat: str | None = None
    ippt: str | None = None
    icms_modelo: str | None = None
    pis_cofins_modelo: str | None = None
    evidencia_nfe: bool = False
    ean_valido_coluna: bool = False
    duplicado_na_planilha: bool = False
    status_planilha: str | None = None
    observacao: str | None = None


class ProductAnalysis(BaseModel):
    """Análise do produto (FASE 5)."""

    model_config = ConfigDict(extra="allow")

    ean: str
    descricao: str
    preco_venda: float
    gate: str  # BLOCKED_*, EAN_OK, etc
    status: ProductStatus
    confidence: str
    risk_level: RiskLevel
    field_provenance: dict[str, Any] = Field(default_factory=dict)
    validation_issues: list[str] = Field(default_factory=list)
    grupo_api_codigo: int | None = None
    centro_api_codigo: int | None = None
    ncm: str | None = None
    cest: str | None = None
    tributo_icms: dict[str, Any] | None = None
    tributo_pis_cofins: dict[str, Any] | None = None


class RegistrationRequest(BaseModel):
    """Requisição HTTP para POST /INTEGRACAO/INCLUIR_PRODUTO."""

    model_config = ConfigDict(extra="allow")

    body_hash: str
    http_status: int | None = None
    ret: str | None = None
    men: str | None = None
    cod_produto: int | None = None
    created_at: datetime | None = None
    body: dict[str, Any] = Field(default_factory=dict)


class ExecutionState(BaseModel):
    """Estado persistente da execução (FASE 4)."""

    model_config = ConfigDict(extra="allow")

    execution_id: str
    started_at: datetime
    checkpoint_index: int = 0
    products_processed: int = 0
    success_count: int = 0
    blocked_count: int = 0
    review_required_count: int = 0
    failed_count: int = 0
    paused_at: datetime | None = None
    paused_reason: str | None = None
    last_result: dict[str, Any] | None = None
    api_rejection_reason: str | None = None
