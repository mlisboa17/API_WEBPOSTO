from __future__ import annotations
from decimal import Decimal, getcontext
from pydantic import BaseModel, Field

getcontext().prec = 18


class ProductMargin(BaseModel):
    sku: str
    units: int = Field(ge=0)
    price: Decimal = Field(...)
    cost: Decimal = Field(...)
    variable_cost: Decimal = Field(default=Decimal('0.00'))

    def gross_profit(self) -> Decimal:
        return self.price - self.cost

    def markup_percent(self) -> Decimal:
        if self.cost == 0:
            return Decimal('0')
        return (self.price - self.cost) / self.cost * Decimal('100')

    def contribution_margin_percent(self) -> Decimal:
        if self.price == 0:
            return Decimal('0')
        return (self.price - self.variable_cost) / self.price * Decimal('100')

    def revenue(self) -> Decimal:
        return self.price * Decimal(self.units)

    def profit_contribution(self) -> Decimal:
        return (self.price - self.variable_cost) * Decimal(self.units)
