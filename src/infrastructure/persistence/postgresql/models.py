"""
PostgreSQL ORM Models: SQLAlchemy 2.0 async-first.

Mapeia entidades de domínio para tabelas PostgreSQL.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Column, String, Integer, Numeric, DateTime, Boolean,
    ForeignKey, JSON, Text, Enum, Index, TIMESTAMP
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum


class Base(DeclarativeBase):
    """Base class para todos os modelos."""
    pass


class SyncStatusEnum(str, enum.Enum):
    """Status de sincronização."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_FAILED = "partially_failed"


# ===== MODELS =====

class EmpresaORM(Base):
    """ORM: Empresa (Tenant)."""
    
    __tablename__ = "empresas"
    
    empresa_id = Column(String(50), primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    config_tipo_rateio = Column(String(20), default="proporcional")
    validar_soma_100 = Column(Boolean, default=True)
    ativo = Column(Boolean, default=True)
    
    timestamp_criacao = Column(DateTime, default=datetime.utcnow)
    timestamp_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    centros_custo = relationship("CentroCustoORM", back_populates="empresa", cascade="all, delete-orphan")
    rateios = relationship("RateioORM", back_populates="empresa", cascade="all, delete-orphan")
    sync_history = relationship("SyncHistoryORM", back_populates="empresa", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_empresas_ativo", "ativo"),
    )


class CentroCustoORM(Base):
    """ORM: Centro de Custo."""
    
    __tablename__ = "centros_custo"
    
    centro_custo_id = Column(String(50), primary_key=True, index=True)
    empresa_id = Column(String(50), ForeignKey("empresas.empresa_id"), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    percentual_padrao = Column(Numeric(5, 2), nullable=False)
    ativo = Column(Boolean, default=True)
    
    timestamp_criacao = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    empresa = relationship("EmpresaORM", back_populates="centros_custo")
    
    __table_args__ = (
        Index("ix_cc_empresa", "empresa_id"),
        Index("ix_cc_ativo", "ativo"),
    )


class RateioORM(Base):
    """ORM: Rateio."""
    
    __tablename__ = "rateios"
    
    rateio_id = Column(String(50), primary_key=True, index=True)
    empresa_id = Column(String(50), ForeignKey("empresas.empresa_id"), nullable=False, index=True)
    lancamento_id = Column(String(50), nullable=False, index=True)
    valor_total = Column(Numeric(19, 2), nullable=False)
    detalhes = Column(JSON, nullable=True)  # Array de centros_custo com percentuais
    
    timestamp_criacao = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    empresa = relationship("EmpresaORM", back_populates="rateios")
    
    __table_args__ = (
        Index("ix_rateio_empresa", "empresa_id"),
        Index("ix_rateio_lancamento", "lancamento_id"),
    )


class SyncHistoryORM(Base):
    """ORM: Histórico de Sincronização."""
    
    __tablename__ = "sync_history"
    
    sync_id = Column(String(50), primary_key=True, index=True)
    empresa_id = Column(String(50), ForeignKey("empresas.empresa_id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")
    
    timestamp_inicio = Column(TIMESTAMP(timezone=True), nullable=False)
    timestamp_fim = Column(TIMESTAMP(timezone=True), nullable=True)
    
    total_lancamentos_processados = Column(Integer, default=0)
    total_rateios_criados = Column(Integer, default=0)
    total_divergencias_detectadas = Column(Integer, default=0)
    total_erros = Column(Integer, default=0)
    duracao_segundos = Column(Numeric(10, 2), nullable=True)
    
    mensagem_erro = Column(Text, nullable=True)
    detalhes = Column(JSON, nullable=True)
    
    timestamp_criacao = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    timestamp_atualizacao = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    empresa = relationship("EmpresaORM", back_populates="sync_history")
    
    __table_args__ = (
        Index("ix_sync_empresa", "empresa_id"),
        Index("ix_sync_status", "status"),
        Index("ix_sync_timestamp", "timestamp_inicio"),
    )


class OutboxEventORM(Base):
    """ORM: Outbox Pattern."""
    
    __tablename__ = "outbox_events"
    
    outbox_id = Column(String(50), primary_key=True, index=True)
    empresa_id = Column(String(50), nullable=False, index=True)
    
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)
    
    timestamp_criacao = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, index=True)
    timestamp_publicacao = Column(TIMESTAMP(timezone=True), nullable=True)
    
    processado = Column(Boolean, default=False, index=True)
    tentativas = Column(Integer, default=0)
    max_tentativas = Column(Integer, default=3)
    mensagem_erro = Column(Text, nullable=True)
    
    timestamp_atualizacao = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_outbox_processado", "processado"),
        Index("ix_outbox_empresa", "empresa_id"),
        Index("ix_outbox_event_type", "event_type"),
        Index("ix_outbox_timestamp", "timestamp_criacao"),
    )


class DomainEventORM(Base):
    """ORM: Domain Events (Event Sourcing)."""
    
    __tablename__ = "domain_events"
    
    event_id = Column(String(50), primary_key=True, index=True)
    empresa_id = Column(String(50), nullable=False, index=True)
    
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)
    
    timestamp_criacao = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, index=True)
    versao = Column(Integer, default=1)
    
    __table_args__ = (
        Index("ix_event_empresa", "empresa_id"),
        Index("ix_event_type", "event_type"),
        Index("ix_event_timestamp", "timestamp_criacao"),
    )


class AdelaideTaxMatrixORM(Base):
    """ORM: cached tax matrix entries used by Adelaide audit flows."""

    __tablename__ = "adelaide_tax_matrix"

    matrix_id = Column(String(64), primary_key=True, index=True)
    uf = Column(String(2), nullable=False, index=True)
    cnae = Column(String(7), nullable=False, index=True)
    ncm = Column(String(8), nullable=False, index=True)
    cst = Column(String(3), nullable=False)
    monofasico = Column(Boolean, default=False)
    aliquota_pis = Column(Numeric(10, 4), default=Decimal("0"))
    aliquota_cofins = Column(Numeric(10, 4), default=Decimal("0"))
    descricao_referencia = Column(String(255), nullable=True)
    timestamp_criacao = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    timestamp_atualizacao = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_adelaide_matrix_lookup", "uf", "cnae", "ncm"),
    )
