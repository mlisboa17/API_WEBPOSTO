"""Contratos publicos versionados do motor de cadastro."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .versions import (
    REGISTRATION_REQUEST_SCHEMA_VERSION,
    REGISTRATION_RESULT_SCHEMA_VERSION,
)

RegistrationStatus = Literal[
    "DRY_RUN",
    "PREFLIGHT_BLOCKED",
    "SKIPPED_PRE_POST",
    "CREATED_AND_VERIFIED",
    "RESULT_UNKNOWN",
    "REJECTED",
    "ALREADY_REGISTERED",
    "ALREADY_REGISTERED_BY_DESCRIPTION",
]


class RiskAuthorization(BaseModel):
    """Autorizacoes explicitas; nenhuma e implicita."""

    model_config = ConfigDict(extra="forbid")

    allow_pending_dfe_cost: bool = False
    accept_fiscal_risk: bool = False
    accept_negative_margin: bool = False
    execute: bool = False


class ProductRegistrationRequest(BaseModel):
    """Solicitacao de cadastro de um produto."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = REGISTRATION_REQUEST_SCHEMA_VERSION
    empresa: int
    centro: int
    ean: str
    descricao: str
    preco_venda: float
    ncm: str
    cest: str | None = None
    unidade: str = "UN"
    grupo_codigo: int | None = None
    custo: float | None = None
    cost_source: str | None = None
    cost_status: str | None = None
    cost_evidence: dict[str, Any] = Field(default_factory=dict)
    perfil_fiscal: dict[str, Any] = Field(default_factory=dict)
    familia_comercial: str | None = None
    authorization: RiskAuthorization = Field(default_factory=RiskAuthorization)


class ProductRegistrationResult(BaseModel):
    """Resultado sanitizado de preflight, cadastro ou verificacao."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = REGISTRATION_RESULT_SCHEMA_VERSION
    status: RegistrationStatus
    ean: str
    empresa: int
    produto_codigo: int | None = None
    referencia: str | None = None
    post_enviado: bool = False
    verificacao: dict[str, Any] = Field(default_factory=dict)
    checkpoint: dict[str, Any] = Field(default_factory=dict)
    riscos: list[str] = Field(default_factory=list)
    evidencias: dict[str, Any] = Field(default_factory=dict)
    body_hash: str | None = None
    body_sanitized: dict[str, Any] = Field(default_factory=dict)
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    dry_run: bool = True
    mensagem: str | None = None
