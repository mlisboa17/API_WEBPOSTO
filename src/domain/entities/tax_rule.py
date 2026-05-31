from __future__ import annotations
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class ProductTaxProfile(BaseModel):
    sku: str
    ncm: str = Field(..., min_length=8, max_length=8)
    cest: str | None = None
    cfop: str | None = None
    cst: str | None = None
    aliquota_icms: Decimal = Field(default=Decimal('0.00'))
    aliquota_pis: Decimal = Field(default=Decimal('0.00'))
    aliquota_cofins: Decimal = Field(default=Decimal('0.00'))

    @field_validator('ncm')
    @classmethod
    def ncm_must_be_digits(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 8:
            raise ValueError('NCM must be 8 digits')
        return v
