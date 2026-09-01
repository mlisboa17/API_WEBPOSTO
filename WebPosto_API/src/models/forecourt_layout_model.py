"""FORECOURT-CONFIG-01A — Configuração operacional da pista (layout).

station_id = empresa_codigo oficial do posto (reutiliza FilialMaster / OFFICIAL_COMPANY_CODES).
pump_id / nozzle_id = códigos ERP reais (bico/bomba) — sem cadastro duplicado.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ForecourtLayout(SQLModel, table=True):
    """Tabela: forecourt_layout."""

    __tablename__ = "forecourt_layout"
    __table_args__ = (
        UniqueConstraint("station_id", "version", name="uq_forecourt_layout_station_version"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    station_id: int = Field(index=True, description="empresa_codigo / posto oficial")
    version: int = Field(default=1, ge=1)
    name: str = Field(default="Layout", max_length=120)
    status: str = Field(default="DRAFT", index=True)  # DRAFT | ACTIVE | ARCHIVED
    mapping_status: str = Field(default="PROVISIONAL")  # PROVISIONAL | CONFIRMED
    valid_from: Optional[datetime] = Field(default=None, index=True)
    valid_to: Optional[datetime] = Field(default=None, index=True)
    coordinate_width: int = Field(default=1000, ge=1)
    coordinate_height: int = Field(default=600, ge=1)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow, index=True)


class ForecourtIsland(SQLModel, table=True):
    """Tabela: forecourt_island."""

    __tablename__ = "forecourt_island"
    __table_args__ = (
        UniqueConstraint("layout_id", "code", name="uq_forecourt_island_layout_code"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    layout_id: int = Field(index=True, foreign_key="forecourt_layout.id")
    code: str = Field(max_length=32)
    name: str = Field(default="", max_length=80)
    zone_code: str = Field(default="", max_length=40, description="Ex: ZONE_LIQUIDOS / ZONE_GNV")
    display_order: int = Field(default=0)
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    width: float = Field(default=120.0)
    height: float = Field(default=80.0)
    active: bool = Field(default=True)


class ServicePosition(SQLModel, table=True):
    """Tabela: service_position — posição operacional (lado da bomba)."""

    __tablename__ = "service_position"
    __table_args__ = (
        UniqueConstraint("layout_id", "code", name="uq_service_position_layout_code"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    layout_id: int = Field(index=True, foreign_key="forecourt_layout.id")
    island_id: int = Field(index=True, foreign_key="forecourt_island.id")
    # pump_id = código bomba ERP (reutilizado; sem tabela duplicada)
    pump_id: int = Field(index=True, description="Código bomba ERP no posto")
    code: str = Field(max_length=32)
    name: str = Field(default="", max_length=80)
    orientation: str = Field(default="AVENIDA", max_length=40)  # AVENIDA | CONVENIENCIA | ...
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    active: bool = Field(default=True)
    operational: bool = Field(default=True)


class ServicePositionNozzle(SQLModel, table=True):
    """Vínculo Position ↔ Bico ERP (nozzle_id = código bico real)."""

    __tablename__ = "service_position_nozzle"
    __table_args__ = (
        UniqueConstraint(
            "layout_id", "nozzle_id", name="uq_service_position_nozzle_layout_bico"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    layout_id: int = Field(index=True, foreign_key="forecourt_layout.id")
    position_id: int = Field(index=True, foreign_key="service_position.id")
    # nozzle_id = código bico ERP
    nozzle_id: int = Field(index=True, description="Código bico ERP")
    station_id: int = Field(index=True, description="Denormalizado p/ isolamento tenant")
    active: bool = Field(default=True)
