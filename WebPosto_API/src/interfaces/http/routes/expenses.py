from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from src.application.usecases.extract_expenses import ExtractExpensesFromCashMovement
from src.interfaces.http.dependencies import get_extract_expenses_usecase

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post("/extract")
async def extract_expenses(
    payload: Dict[str, Any],
    use_case: ExtractExpensesFromCashMovement = Depends(get_extract_expenses_usecase),
):
    expenses = await use_case.execute(payload)
    return {
        "count": len(expenses),
        "items": [item.model_dump(mode="json") for item in expenses],
    }
