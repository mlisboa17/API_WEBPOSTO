"""
SQLAlchemy Declarative Models for Empresa and Rateio (1:1 Domain Mapping)
"""
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Numeric, ForeignKey, DateTime, JSON, event
from sqlalchemy.ext.asyncio import AsyncAttrs
from src.infrastructure.base import Base
from src.infrastructure.checksum import calculate_checksum
from typing import List, Optional
from decimal import Decimal
import datetime
from datetime import timezone


class Empresa(AsyncAttrs, Base):
    __tablename__ = "empresas"
    empresa_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    config_tipo_rateio: Mapped[str] = mapped_column(String(32), nullable=False)
    validar_soma_100: Mapped[bool] = mapped_column()
    ativo: Mapped[bool] = mapped_column()
    version: Mapped[int] = mapped_column(Integer, default=1, onupdate=lambda: lambda: None)  # Incremented manually
    checksum: Mapped[str] = mapped_column(String(16), default="")  # SHA256[:16]
    timestamp_criacao: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.datetime.now(timezone.utc))
    centros_custo: Mapped[Optional[List["CentroCusto"]]] = relationship("CentroCusto", back_populates="empresa")
    rateios: Mapped[Optional[List["Rateio"]]] = relationship("Rateio", back_populates="empresa")

class CentroCusto(AsyncAttrs, Base):
    __tablename__ = "centros_custo"
    centro_custo_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.empresa_id"))
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    percentual_padrao: Mapped[Decimal] = mapped_column(Numeric(8,4))
    version: Mapped[int] = mapped_column(Integer, default=1)
    checksum: Mapped[str] = mapped_column(String(16), default="")
    empresa: Mapped["Empresa"] = relationship("Empresa", back_populates="centros_custo")

class Rateio(AsyncAttrs, Base):
    __tablename__ = "rateios"
    rateio_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.empresa_id"))
    lancamento_id: Mapped[str] = mapped_column(String(36), nullable=False)
    valor_total: Mapped[Decimal] = mapped_column(Numeric(18,4))
    detalhes: Mapped[dict] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)
    checksum: Mapped[str] = mapped_column(String(16), default="")
    empresa: Mapped["Empresa"] = relationship("Empresa", back_populates="rateios")
    timestamp_criacao: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.datetime.now(timezone.utc))


# Event listeners for automatic checksum calculation
def _calculate_checksum(mapper, connection, target):
    """Calculate checksum before insert/update."""
    data = {
        column.name: getattr(target, column.name)
        for column in mapper.columns
    }
    target.checksum = calculate_checksum(data)


event.listen(Empresa, 'before_insert', _calculate_checksum, propagate=True)
event.listen(Empresa, 'before_update', _calculate_checksum, propagate=True)
event.listen(CentroCusto, 'before_insert', _calculate_checksum, propagate=True)
event.listen(CentroCusto, 'before_update', _calculate_checksum, propagate=True)
event.listen(Rateio, 'before_insert', _calculate_checksum, propagate=True)
event.listen(Rateio, 'before_update', _calculate_checksum, propagate=True)
