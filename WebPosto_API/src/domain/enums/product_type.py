"""Enum padronizado de tipos de produto WebPosto — Sprint 45."""

from __future__ import annotations

from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, field_validator


class ProductType(str, Enum):
    """Tipos de produto do WebPosto com fallback seguro para novos códigos."""

    COMBUSTIVEL = "C"
    PRODUTO = "P"
    UTILIDADE = "U"
    INSUMO = "I"
    OUTRO = "O"
    SERVICO = "S"
    KIT = "K"
    CODIGO_8 = "8"
    DESCONHECIDO = "?"

    @classmethod
    def from_webposto(cls, value: str | None) -> ProductType:
        if not value:
            return cls.DESCONHECIDO
        normalized = str(value).strip().upper()
        try:
            return cls(normalized)
        except ValueError:
            return cls.DESCONHECIDO

    @property
    def is_fuel(self) -> bool:
        return self == ProductType.COMBUSTIVEL

    @property
    def is_convenience(self) -> bool:
        return self in {ProductType.PRODUTO, ProductType.KIT}

    @property
    def department(self) -> str | None:
        if self.is_fuel:
            return "combustiveis"
        if self.is_convenience:
            return "conveniencia"
        if self == ProductType.UTILIDADE:
            return "lubrificantes"
        return None

    @property
    def label(self) -> str:
        labels = {
            ProductType.COMBUSTIVEL: "Combustível",
            ProductType.PRODUTO: "Produto/Conveniência",
            ProductType.UTILIDADE: "Utilidade/Lubrificante",
            ProductType.INSUMO: "Insumo",
            ProductType.OUTRO: "Outro",
            ProductType.SERVICO: "Serviço",
            ProductType.KIT: "Kit",
            ProductType.CODIGO_8: "Código 8",
            ProductType.DESCONHECIDO: "Não classificado",
        }
        return labels.get(self, "Desconhecido")


class ProductTypeInfo(BaseModel):
    """DTO enriquecido com informações do tipo de produto."""

    model_config = ConfigDict(frozen=True)

    code: str
    type: ProductType
    department: str | None
    label: str
    is_fuel: bool
    is_convenience: bool

    FUEL_CODES: ClassVar[frozenset[str]] = frozenset({"C"})
    CONVENIENCE_CODES: ClassVar[frozenset[str]] = frozenset({"P", "K"})
    LUBRICANT_CODES: ClassVar[frozenset[str]] = frozenset({"U"})

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: object) -> str:
        return str(value).strip().upper() if value else "?"

    @classmethod
    def from_raw(cls, raw_code: str | None) -> ProductTypeInfo:
        product_type = ProductType.from_webposto(raw_code)
        return cls(
            code=raw_code or "?",
            type=product_type,
            department=product_type.department,
            label=product_type.label,
            is_fuel=product_type.is_fuel,
            is_convenience=product_type.is_convenience,
        )
