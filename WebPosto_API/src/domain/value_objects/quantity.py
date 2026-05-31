from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class Quantity(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: Decimal
    unit: str = "UN"

    @field_validator("value", mode="before")
    @classmethod
    def parse_value(cls, v):
        return Decimal(str(v or 0))
