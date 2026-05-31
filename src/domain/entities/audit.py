from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, Extra, IPvAnyAddress, condecimal


class Role(str, Enum):
    ADMIN = "admin"
    DIRECTOR = "director"
    OPERATOR = "operator"
    VIEWER = "viewer"


class MetricSnapshot(BaseModel):
    """Domain entity representing an aggregated metric snapshot."""

    source: str
    total_sales: condecimal(max_digits=12, decimal_places=4) = Field(...)
    net_margin: condecimal(max_digits=12, decimal_places=4) = Field(...)
    tax_collected: condecimal(max_digits=12, decimal_places=4) = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"extra": Extra.forbid}


class AuditLog(BaseModel):
    """Audit log entry domain entity."""

    id: str | None = None
    timestamp: datetime
    action: str
    user_email: str
    ip_address: IPvAnyAddress
    status: str
    checksum: str | None = None

    model_config = {"extra": Extra.forbid}
