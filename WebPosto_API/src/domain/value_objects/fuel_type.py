from __future__ import annotations

from enum import Enum


class FuelType(str, Enum):
    GASOLINA_COMUM = "GASOLINA_COMUM"
    GASOLINA_ADITIVADA = "GASOLINA_ADITIVADA"
    ETANOL = "ETANOL"
    DIESEL = "DIESEL"
    GNV = "GNV"
    OUTRO = "OUTRO"

    @classmethod
    def from_product_name(cls, nome: str) -> "FuelType":
        n = (nome or "").upper()
        if "ETANOL" in n or "ETAN" in n:
            return cls.ETANOL
        if "DIESEL" in n or "S10" in n or "S500" in n:
            return cls.DIESEL
        if "GNV" in n:
            return cls.GNV
        if "ADITIV" in n or "GRID" in n or "V-POWER" in n:
            return cls.GASOLINA_ADITIVADA
        if "GASOL" in n:
            return cls.GASOLINA_COMUM
        return cls.OUTRO
