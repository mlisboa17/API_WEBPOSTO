from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CashExpense(BaseModel):
    """Entidade de domínio para despesas normalizadas do gateway."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=8, max_length=128)
    posto_id: str = Field(min_length=1, max_length=64)
    valor: Decimal
    descricao: str = Field(min_length=1, max_length=500)
    timestamp: datetime

    @field_validator("valor", mode="before")
    @classmethod
    def validate_valor(cls, value: object) -> Decimal:
        if isinstance(value, float):
            raise TypeError("Use Decimal/string/integer for monetary values")
        dec = Decimal(str(value))
        return dec.quantize(Decimal("0.01"))
