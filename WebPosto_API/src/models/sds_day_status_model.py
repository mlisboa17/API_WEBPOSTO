"""Checkpoint operacional por unidade/dia do SDS. Sem segredos."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class SdsDayStatusModel(SQLModel, table=True):
    __tablename__ = "sds_day_status"
    __table_args__ = (
        UniqueConstraint("empresa_codigo", "data_referencia", name="uq_sds_day_status_empresa_data"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_codigo: int = Field(index=True)
    data_referencia: date = Field(index=True)
    status: str = Field(default="PENDENTE", max_length=40)
    registros_sem_identidade: int = Field(default=0)
    quantidade_abastecimentos: Optional[int] = None
    tentativas: int = Field(default=0)
    mensagem: str = Field(default="", max_length=400)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
