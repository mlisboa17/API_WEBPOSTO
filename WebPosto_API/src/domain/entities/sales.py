"""Entidades de vendas — domínio puro."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.domain.value_objects.money import Money
from src.domain.value_objects.payment_method import PaymentMethod
from src.domain.value_objects.quantity import Quantity


class SaleLineItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    produto_codigo: int
    descricao: str
    quantidade: Quantity
    valor_unitario: Money
    valor_total: Money


class SalesInvoice(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    data_emissao: datetime
    filial_codigo: Optional[int] = None
    forma_pagamento: PaymentMethod = PaymentMethod.OUTRO
    valor_total: Money
    itens: List[SaleLineItem] = Field(default_factory=list)


class TankVolume(BaseModel):
    model_config = ConfigDict(frozen=True)

    tanque_codigo: int
    produto_codigo: Optional[int] = None
    produto_nome: str = ""
    volume_litros: Quantity
    capacidade_litros: Optional[Quantity] = None
    medido_em: Optional[datetime] = None


class Filial(BaseModel):
    model_config = ConfigDict(frozen=True)

    codigo: int
    razao_social: str = ""
    nome_fantasia: str = ""
    cnpj: Optional[str] = None


class Product(BaseModel):
    model_config = ConfigDict(frozen=True)

    codigo: int
    descricao: str
    grupo_codigo: Optional[int] = None
    preco_venda: Money
    preco_custo: Money
    ativo: bool = True
