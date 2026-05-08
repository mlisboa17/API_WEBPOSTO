from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ClienteModel(Base):
    """ORM Model: Cliente"""

    __tablename__ = "clientes"

    id = Column(String(36), primary_key=True)
    nome = Column(String(255), nullable=False)
    cnpj = Column(String(20), nullable=False, unique=True, index=True)
    ativo = Column(Boolean, default=True, index=True)
    webposto_id = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AbastecimentoModel(Base):
    """ORM Model: Abastecimento"""

    __tablename__ = "abastecimentos"

    id = Column(String(36), primary_key=True)
    cliente_id = Column(String(36), nullable=False, index=True)
    data = Column(DateTime, nullable=False, index=True)
    valor = Column(Float, nullable=False)
    litros = Column(Float, nullable=False)
    produto_id = Column(String(36), nullable=True)
    webposto_id = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FinanceiroModel(Base):
    """ORM Model: Financeiro"""

    __tablename__ = "financeiro"

    id = Column(String(36), primary_key=True)
    tipo = Column(
        String(20), nullable=False, index=True
    )  # RECEBER, PAGAR, TRANSFERENCIA
    valor = Column(Float, nullable=False)
    data_vencimento = Column(DateTime, nullable=False, index=True)
    descricao = Column(String(255), nullable=False)
    pago = Column(Boolean, default=False, index=True)
    data_pagamento = Column(DateTime, nullable=True)
    webposto_id = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CaixaModel(Base):
    """ORM Model: Caixa"""

    __tablename__ = "caixa"

    id = Column(String(36), primary_key=True)
    descricao = Column(String(255), nullable=False)
    saldo = Column(Float, default=0.0)
    data_movimento = Column(DateTime, nullable=False, index=True)
    referencia = Column(String(255), nullable=True, unique=True)
    webposto_id = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
