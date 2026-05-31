from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import ConfigDict, field_validator
from sqlmodel import SQLModel, Field


class CashExpense(SQLModel):
    """Immutable domain entity for cash expenses."""

    id: Optional[str] = Field(default=None, primary_key=True)
    posto_id: str = Field(index=True)
    valor: Decimal = Field(max_digits=14, decimal_places=2)
    descricao: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    origem: str = Field(default="webposto")

    model_config = ConfigDict(frozen=True)

    @field_validator("valor")
    @classmethod
    def validate_valor(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("valor must be a finite decimal")
        return value


class PostoCredentials(SQLModel):
    """Credentials stored per posto in local SQLite."""

    id: Optional[str] = None
    posto_id: str
    api_key: str = Field(repr=False)
    api_secret: str = Field(repr=False)
    status: str = "ativa"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(frozen=True)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        allowed = {"ativa", "inativa"}
        if value not in allowed:
            raise ValueError("status must be 'ativa' or 'inativa'")
        return value


class PostoCredentialsRecord(SQLModel, table=True):
    """SQLite persistence model for posto credentials."""

    id: Optional[str] = Field(default=None, primary_key=True)
    posto_id: str = Field(index=True, unique=True)
    api_key: str
    api_secret: str
    status: str = Field(default="ativa")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TenantPosto(SQLModel):
    """Immutable tenant metadata used for multi-tenant WebPosto calls."""

    id: str
    nome_posto: str
    webposto_base_url: str
    api_key: str = Field(repr=False)
    ativo: bool = True

    model_config = ConfigDict(frozen=True)

    @field_validator("webposto_base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("webposto_base_url must be provided")
        return value.strip()

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("api_key must be provided")
        return value.strip()


class TenantPostoRecord(SQLModel, table=True):
    """SQLite persistence model for tenant posto configuration."""

    id: str = Field(primary_key=True)
    nome_posto: str
    webposto_base_url: str
    api_key: str
    ativo: bool = Field(default=True)


class MovimentoContaItem(SQLModel):
    """Schema mapper for /INTEGRACAO/MOVIMENTO_CONTA payload items."""

    id: Optional[str] = None
    tipo: str
    historico: str = "Despesa de Caixa"
    valor: Decimal = Field(max_digits=14, decimal_places=2)
    data: datetime

    model_config = ConfigDict(frozen=True)

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, value: str) -> str:
        if value.upper() not in {"DEBITO", "CREDITO"}:
            raise ValueError("tipo must be DEBITO or CREDITO")
        return value.upper()

    @field_validator("valor")
    @classmethod
    def validate_monetary_value(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("valor must be a finite decimal")
        return value
