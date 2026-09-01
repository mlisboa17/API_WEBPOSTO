"""Contratos departamentais de Combustíveis."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.core.management_scope import is_licensed_company


class FuelVolumeFact(BaseModel):
    """Volume vendido comprovado pelo LMC para uma empresa licenciada."""

    model_config = ConfigDict(frozen=True)

    empresa_codigo: int
    produto_codigo: int = Field(..., gt=0)
    produto_lmc_codigo: int | None = None
    combustivel: str = Field(..., min_length=1)
    data_referencia: str = ""
    litros: Decimal = Field(..., gt=0)
    departamento: Literal["combustiveis"] = "combustiveis"
    fonte: Literal["CONSULTAR_LMC_REDE"] = "CONSULTAR_LMC_REDE"

    @field_validator("empresa_codigo")
    @classmethod
    def empresa_deve_estar_licenciada(cls, value: int) -> int:
        if not is_licensed_company(value):
            raise ValueError("empresa fora do escopo licenciado")
        return value

    @field_validator("litros", mode="before")
    @classmethod
    def normalizar_litros(cls, value: object) -> Decimal:
        try:
            return Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        except Exception as exc:
            raise ValueError("volume de combustível inválido") from exc


class FuelSaleItemFact(BaseModel):
    """Item vendido classificado como combustível por evidência operacional."""

    model_config = ConfigDict(frozen=True)

    empresa_codigo: int
    venda_codigo: int = Field(..., gt=0)
    venda_item_codigo: int = Field(..., gt=0)
    produto_codigo: int = Field(..., gt=0)
    grupo_codigo: int | None = None
    produto_lmc_codigo: int | None = None
    bico_codigo: int | None = None
    tanque_codigo: int | None = None
    data_movimento: str
    litros: Decimal = Field(..., gt=0)
    preco_venda: Decimal = Field(default=Decimal("0"), ge=0)
    preco_custo: Decimal = Field(default=Decimal("0"), ge=0)
    faturamento: Decimal = Field(default=Decimal("0"), ge=0)
    custo_total: Decimal = Field(default=Decimal("0"), ge=0)
    desconto_total: Decimal = Field(default=Decimal("0"), ge=0)
    acrescimo_total: Decimal = Field(default=Decimal("0"), ge=0)
    departamento: Literal["combustiveis"] = "combustiveis"
    fonte: Literal["VENDA_ITEM"] = "VENDA_ITEM"

    @field_validator("empresa_codigo")
    @classmethod
    def empresa_deve_estar_licenciada(cls, value: int) -> int:
        if not is_licensed_company(value):
            raise ValueError("empresa fora do escopo licenciado")
        return value

    @field_validator(
        "litros",
        "preco_venda",
        "preco_custo",
        "faturamento",
        "custo_total",
        "desconto_total",
        "acrescimo_total",
        mode="before",
    )
    @classmethod
    def normalizar_decimal(cls, value: object) -> Decimal:
        try:
            return Decimal(str(value or 0)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        except Exception as exc:
            raise ValueError("valor numérico inválido") from exc

    @model_validator(mode="after")
    def exigir_evidencia_de_combustivel(self) -> "FuelSaleItemFact":
        if self.grupo_codigo != 24554 and not any(
            value not in (None, 0) for value in (self.produto_lmc_codigo, self.bico_codigo, self.tanque_codigo)
        ):
            raise ValueError("item sem evidência operacional de combustível")
        return self
