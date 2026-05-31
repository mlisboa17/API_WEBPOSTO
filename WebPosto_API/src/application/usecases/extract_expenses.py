from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.entities.cash_expense import Amount, CashExpense, CashMovementId, ExpenseCategory
from src.domain.events.cash_expense_events import CashExpenseDetected
from src.infrastructure.algorithms.expense_classifier import map_description_to_category


class ExpenseLineInput(BaseModel):
    model_config = ConfigDict(strict=True)

    description: str = Field(min_length=1, max_length=400)
    amount: Decimal

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, value: object) -> Decimal:
        if isinstance(value, float):
            raise TypeError("float is not allowed for amount")
        dec = Decimal(str(value))
        if dec <= 0:
            raise ValueError("amount must be > 0")
        if dec != dec.quantize(Decimal("0.01")):
            raise ValueError("amount must have at most 2 decimal places")
        return dec


class ExtractExpensesRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    cash_movement_id: str = Field(min_length=1, max_length=120)
    expenses: List[ExpenseLineInput] = Field(default_factory=list)


class ExtractExpensesFromCashMovement:
    def __init__(self, event_bus: Any | None = None) -> None:
        self._event_bus = event_bus

    @staticmethod
    def _expense_id(movement_id: str, description: str, amount: Decimal) -> str:
        raw = f"{movement_id}|{description.strip().lower()}|{amount}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def execute(self, payload: Dict[str, Any] | ExtractExpensesRequest) -> List[CashExpense]:
        req = payload if isinstance(payload, ExtractExpensesRequest) else ExtractExpensesRequest.model_validate(payload)

        output: List[CashExpense] = []
        for item in req.expenses:
            category: ExpenseCategory = map_description_to_category(item.description)
            expense = CashExpense(
                id=self._expense_id(req.cash_movement_id, item.description, item.amount),
                cash_movement_id=CashMovementId(value=req.cash_movement_id),
                description=item.description.strip(),
                amount=Amount(value=item.amount),
                category=category,
            )
            output.append(expense)

            if self._event_bus is not None:
                event = CashExpenseDetected(
                    aggregate_id=req.cash_movement_id,
                    expense_id=expense.id,
                    cash_movement_id=req.cash_movement_id,
                    category=expense.category.value,
                    amount=float(expense.amount.value),
                    description=expense.description,
                    detected_at=expense.detected_at,
                )
                try:
                    await self._event_bus.publish(event)
                except Exception:
                    # Event bus indisponível não deve impedir a extração.
                    pass

        return output
