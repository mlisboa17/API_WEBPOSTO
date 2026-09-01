"""Autodiscovery de produtos por filial — arquitetura híbrida."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class CompanyProductModel(SQLModel, table=True):
    """Árvore dinâmica de produtos descobertos via WebPosto (sem cadastro manual)."""

    __tablename__ = "company_products"
    __table_args__ = (
        UniqueConstraint(
            "empresa_codigo",
            "codigo_produto_webposto",
            name="uq_company_products_empresa_codigo",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_codigo: int = Field(index=True)
    codigo_produto_webposto: str = Field(index=True, max_length=64)
    nome_produto: str = Field(default="", max_length=255)
    categoria: str = Field(default="OUTROS", index=True, max_length=64)
    is_aditivado: bool = Field(default=False, index=True)
    ativo: bool = Field(default=True, index=True)
    ultima_venda_em: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
