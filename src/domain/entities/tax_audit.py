from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


FOUR_DECIMALS = Decimal("0.0001")


def _quantize_decimal(value: Decimal) -> Decimal:
    return value.quantize(FOUR_DECIMALS)


class FiscalMatrix(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    uf: str = Field(..., min_length=2, max_length=2)
    regime: Literal["LUCRO_REAL", "LUCRO_PRESUMIDO"]
    cnae: str = Field(..., min_length=7, max_length=7)
    ncm: str = Field(..., min_length=8, max_length=8)
    cest: str | None = Field(default=None, min_length=7, max_length=7)
    cst: str = Field(..., min_length=2, max_length=3)
    monofasico: bool = False
    aliquota_pis: Decimal = Field(default=Decimal("0.0000"), max_digits=12, decimal_places=4)
    aliquota_cofins: Decimal = Field(default=Decimal("0.0000"), max_digits=12, decimal_places=4)
    aliquota_icms: Decimal = Field(default=Decimal("0.0000"), max_digits=12, decimal_places=4)
    effective_tax_rate: Decimal = Field(default=Decimal("0.0000"), max_digits=12, decimal_places=4)
    source: str = "BASE_NACIONAL_2026_PE"

    @field_validator("uf")
    @classmethod
    def validate_uf(cls, value: str) -> str:
        normalized = value.upper()
        if len(normalized) != 2 or not normalized.isalpha():
            raise ValueError("UF must contain 2 letters")
        return normalized

    @field_validator("ncm")
    @classmethod
    def validate_ncm(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 8:
            raise ValueError("NCM must contain 8 digits")
        return value

    @field_validator("cest")
    @classmethod
    def validate_cest(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.isdigit() or len(value) != 7:
            raise ValueError("CEST must contain 7 digits")
        return value

    @field_validator("aliquota_pis", "aliquota_cofins", "aliquota_icms", "effective_tax_rate")
    @classmethod
    def quantize_rates(cls, value: Decimal) -> Decimal:
        return _quantize_decimal(value)


class SaleAuditRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    sku: str = Field(..., min_length=1)
    description: str = Field(..., min_length=3)
    sold_at: datetime
    quantity: int = Field(..., ge=1)
    price: Decimal = Field(..., max_digits=12, decimal_places=4)
    cost: Decimal = Field(..., max_digits=12, decimal_places=4)
    effective_tax: Decimal = Field(default=Decimal("0.0000"), max_digits=12, decimal_places=4)
    card_fee: Decimal = Field(default=Decimal("0.0000"), max_digits=12, decimal_places=4)
    cost_center: Decimal = Field(default=Decimal("0.0000"), max_digits=12, decimal_places=4)
    tax_rate: Decimal = Field(default=Decimal("0.0000"), max_digits=12, decimal_places=4)
    ncm: str = Field(..., min_length=8, max_length=8)
    cest: str | None = Field(default=None, min_length=7, max_length=7)
    cst: str = Field(default="01", min_length=2, max_length=3)
    cnae: str = Field(default="4731800", min_length=7, max_length=7)
    uf: str = Field(default="PE", min_length=2, max_length=2)
    regime: Literal["LUCRO_REAL", "LUCRO_PRESUMIDO"] = "LUCRO_REAL"

    @field_validator("price", "cost", "effective_tax", "card_fee", "cost_center", "tax_rate")
    @classmethod
    def quantize_amounts(cls, value: Decimal) -> Decimal:
        return _quantize_decimal(value)


class TaxDiscrepancy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    sku: str = Field(..., min_length=1)
    local_ncm: str = Field(..., min_length=8, max_length=8)
    national_ncm: str = Field(..., min_length=8, max_length=8)
    local_rate: Decimal = Field(..., ge=Decimal("0.0000"), le=Decimal("100.0000"), max_digits=12, decimal_places=4)
    national_rate: Decimal = Field(..., ge=Decimal("0.0000"), le=Decimal("100.0000"), max_digits=12, decimal_places=4)
    discrepancy_amount: Decimal = Field(..., max_digits=12, decimal_places=4)
    severity: Literal["ok", "alerta", "critico"] = "alerta"
    reason: str = Field(default="", min_length=0)
    checksum: str = Field(default="", min_length=0)

    @field_validator("local_ncm", "national_ncm")
    @classmethod
    def validate_discrepancy_ncm(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 8:
            raise ValueError("NCM must contain 8 digits")
        return value

    @field_validator("local_rate", "national_rate", "discrepancy_amount")
    @classmethod
    def quantize_discrepancy_fields(cls, value: Decimal) -> Decimal:
        return _quantize_decimal(value)
