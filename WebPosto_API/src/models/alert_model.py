"""Modelos de dados para Alertas Executivos — Sprint 50."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class AlertCategory(str, Enum):
    QUEBRA_CAIXA = "QUEBRA_CAIXA"
    DESVIO_TANQUE = "DESVIO_TANQUE"
    ESTOURO_VACUO = "ESTOURO_VACUO"
    RUPTURA_CURVA_A = "RUPTURA_CURVA_A"


class AlertSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"


class ExecutiveAlertModel(SQLModel, table=True):
    """ORM Model: Alerta Executivo Proativo"""

    __tablename__ = "executive_alerts"

    id: Optional[int] = Field(default=None, primary_key=True)
    alert_external_id: str = Field(index=True, unique=True) # Para idempotência (ex: break_11495_2026-07-25)
    category: AlertCategory = Field(index=True)
    severity: AlertSeverity = Field(index=True)
    title: str
    description: str
    impact_rs: Optional[float] = None
    unit_id: Optional[int] = Field(default=None, index=True) # empresa_codigo
    data_referencia: str = Field(index=True)
    
    metadata_json: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    is_resolved: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
