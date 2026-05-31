from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class NCMModel(BaseModel):
    code: str = Field(..., min_length=8, max_length=8)

    @field_validator("code")
    @classmethod
    def validate_ncm(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 8:
            raise ValueError("NCM must be 8 digits")
        return v


class SaleRecord(BaseModel):
    id: str
    sold_at: datetime
    gross: float
    cost: float
    ncm: Optional[str] = None
    card_fee_pct: float = 0.0


class TaxResult(BaseModel):
    pis_cofins_recoverable: float = 0.0
    validated: bool = True
