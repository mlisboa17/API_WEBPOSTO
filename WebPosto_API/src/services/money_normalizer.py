from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def parse_decimal_br(value: Any) -> Decimal:
    """Parseia formatos monetarios comuns (BR/US) para Decimal."""
    if value is None:
        return Decimal("0")

    if isinstance(value, Decimal):
        return value

    if isinstance(value, bool):
        return Decimal("0")

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    text = str(value).strip()
    if not text:
        return Decimal("0")

    negative = text.startswith("-")
    clean = text.lstrip("+-").replace("R$", "").replace(" ", "")

    if "," in clean and "." in clean:
        # Ex.: 13.200,00
        clean = clean.replace(".", "").replace(",", ".")
    elif "," in clean:
        # Ex.: 1320,00
        clean = clean.replace(",", ".")

    try:
        number = Decimal(clean)
    except InvalidOperation:
        return Decimal("0")

    return -number if negative else number


def normalize_cents(value: Any) -> Decimal:
    """Interpreta o valor como centavos inteiros."""
    raw = parse_decimal_br(value)
    return (raw / Decimal("100")).quantize(Decimal("0.01"))


def normalize_webposto_money(value: Any) -> Decimal:
    """
    Normalizacao generica: aceita string BR/US e inteiros em centavos.
    Regras:
    - inteiro numerico sem separador >= 5 digitos: assume centavos
    - formato com separador decimal: respeita decimal informado
    """
    if value is None:
        return Decimal("0")

    if isinstance(value, str):
        raw = value.strip().replace("R$", "").replace(" ", "")
        digits_only = raw.lstrip("+-").isdigit()
        if digits_only and len(raw.lstrip("+-")) >= 5:
            return normalize_cents(raw)
        return parse_decimal_br(raw).quantize(Decimal("0.01"))

    if isinstance(value, int):
        if abs(value) >= 10000:
            return normalize_cents(value)
        return Decimal(value).quantize(Decimal("0.01"))

    return parse_decimal_br(value).quantize(Decimal("0.01"))


def normalize_webposto_expense_value(value: Any) -> Decimal:
    """
    DESPESAS_FINANCEIRO_REDE atualmente chega em decimal correto.
    Mantem decimal informado e evita divisao cega por 100.
    """
    return parse_decimal_br(value).quantize(Decimal("0.01"))


def normalize_webposto_sale_value(value: Any) -> Decimal:
    """Normaliza valor de vendas sem aplicar regra cega de centavos."""
    return parse_decimal_br(value).quantize(Decimal("0.01"))


def normalize_webposto_account_value(value: Any) -> Decimal:
    """Normaliza valor financeiro (contas) preservando decimal informado."""
    return parse_decimal_br(value).quantize(Decimal("0.01"))
