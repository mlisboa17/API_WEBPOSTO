"""Contratos canônicos da camada de fatos departamentalizados."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.core.management_scope import DepartmentId


class DepartmentalFactKind(str, Enum):
    SALE = "SALE"
    COST = "COST"
    EXPENSE = "EXPENSE"
    STOCK = "STOCK"
    CASH = "CASH"


class DepartmentalFactStatus(str, Enum):
    CLASSIFIED = "CLASSIFIED"
    QUARANTINED = "QUARANTINED"


class FactLineage(BaseModel):
    model_config = ConfigDict(frozen=True)

    logical_token: str
    endpoint: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    collected_at: datetime


class DepartmentalFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    fact_id: str
    kind: DepartmentalFactKind
    empresa_codigo: int
    departamento: Optional[DepartmentId] = None
    status: DepartmentalFactStatus
    quarantine_reason: Optional[str] = None
    source_record_id: str
    produto_codigo: Optional[int] = None
    grupo_codigo: Optional[int] = None
    data_movimento: Optional[datetime] = None
    turno_codigo: Optional[int] = None
    quantidade: Decimal = Decimal("0")
    valor: Decimal = Decimal("0")
    lineage: FactLineage


class DepartmentalFactBatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    facts: list[DepartmentalFact] = Field(default_factory=list)
    quarantine: list[DepartmentalFact] = Field(default_factory=list)
    rejected_unlicensed: int = 0
    duplicates_removed: int = 0
    identity_conflicts: int = 0
    source_total: Decimal = Decimal("0")
    reconciled_total: Decimal = Decimal("0")
    reconciliation_difference: Decimal = Decimal("0")
