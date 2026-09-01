"""Consolidação diária de vendas por empresa/produto — banco híbrido local."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class SalesDailySummaryModel(SQLModel, table=True):
    """Fechamento diário por filial e produto (origem bomba / ABASTECIMENTO)."""

    __tablename__ = "sales_daily_summary"
    __table_args__ = (
        UniqueConstraint(
            "empresa_codigo",
            "data_referencia",
            "codigo_produto_webposto",
            name="uq_sales_daily_empresa_data_produto",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_codigo: int = Field(index=True)
    data_referencia: date = Field(index=True)
    codigo_produto_webposto: str = Field(index=True, max_length=64)
    nome_produto: str = Field(default="", max_length=255)
    categoria: str = Field(default="OUTROS", max_length=64)
    litros_vendidos: float = Field(default=0.0)
    faturamento_bruto: float = Field(default=0.0)
    quantidade_abastecimentos: int = Field(default=0)
    custo_medio_ponderado: float = Field(default=0.0)
    margem_bruta_real: float = Field(default=0.0)
    synced_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )
