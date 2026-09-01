"""Modelo de persistência para preços de concorrentes (Competitividade Regional)."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class CompetitorPriceModel(SQLModel, table=True):
    __tablename__ = "competitor_prices"

    id: Optional[int] = Field(default=None, primary_key=True)
    concorrente_nome: str
    produto_codigo: str
    produto_nome: str
    preco_venda_rs: float
    datahora: datetime
    unidade_codigo: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
