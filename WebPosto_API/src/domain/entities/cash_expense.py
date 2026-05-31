from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

_CENT = Decimal("0.01")


class CashMovementId(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: str = Field(min_length=1, max_length=120)


class ExpenseCategory(str, Enum):
    FUEL = "fuel"
    TAX = "tax"
    PAYROLL = "payroll"
    MAINTENANCE = "maintenance"
    RENT = "rent"
    UTILITIES = "utilities"
    SERVICE = "service"
    OTHER = "other"


class Amount(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: Decimal = Field(description="Monetary amount with strict cents precision")

    @field_validator("value", mode="before")
    @classmethod
    def parse_amount(cls, value: object) -> Decimal:
        if isinstance(value, float):
            raise TypeError("Use Decimal, str or int; float is not allowed")
        dec = Decimal(str(value))
        if dec != dec.quantize(_CENT):
            raise ValueError("Amount must have at most 2 decimal places")
        return dec


class CashExpense(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=8, max_length=128)
    cash_movement_id: CashMovementId
    description: str = Field(min_length=1, max_length=400)
    amount: Amount
    category: ExpenseCategory = ExpenseCategory.OTHER
    detected_at: datetime = Field(default_factory=datetime.utcnow)
