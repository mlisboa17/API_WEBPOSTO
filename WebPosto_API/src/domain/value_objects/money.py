"""Value objects — sem dependências HTTP."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from pydantic import BaseModel, ConfigDict, field_validator


class Money(BaseModel):
    model_config = ConfigDict(frozen=True)

    amount: Decimal
    currency: str = "BRL"

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, v):
        if v is None:
            return Decimal("0")
        return Decimal(str(v)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    def __str__(self) -> str:
        return f"R$ {self.amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
