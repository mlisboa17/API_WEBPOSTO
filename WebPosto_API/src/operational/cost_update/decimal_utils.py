"""Conversao monetaria com Decimal. Nenhum calculo usa float."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

COST_QUANTUM = Decimal("0.0001")
PRESENT_QUANTUM = Decimal("0.01")
PERCENT_QUANTUM = Decimal("0.0001")


def to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise TypeError("bool nao e valor monetario")
    return Decimal(str(value))


def optional_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return to_decimal(value)


def quantize_cost(value: Decimal) -> Decimal:
    return value.quantize(COST_QUANTUM)


def present_money(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value.quantize(PRESENT_QUANTUM, rounding=ROUND_HALF_UP))


def present_percent(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str((value * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def ratio(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return (numerator / denominator).quantize(PERCENT_QUANTUM)
