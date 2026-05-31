"""
Contratos Pydantic v2 — catálogo de produtos WebPosto (INTEGRACAO/PRODUTO).
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

DECIMAL_Q = Decimal("0.0001")


def _d(value) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value)).quantize(DECIMAL_Q, rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0")


class WebPostoProdutoSchema(BaseModel):
    """Produto normalizado a partir da API Quality (campos reais + aliases)."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=False)

    id: int = Field(..., description="Código do produto no WebPosto")
    codigo_barra: Optional[str] = Field(None, alias="codigoBarras")
    descricao: str
    preco_venda: Decimal = Field(
        default=Decimal("0"),
        alias="precoVenda",
        description="Preço de venda tabela A",
    )
    preco_custo: Decimal = Field(default=Decimal("0"), alias="precoCusto")
    ativo: bool = True
    estoque_atual: Decimal = Field(default=Decimal("0"), alias="estoqueAtual")
    unidade_medida: str = Field(default="UN", alias="unidadeMedida")
    ncm: Optional[str] = None
    cest: Optional[str] = None
    cst_icms: Optional[str] = Field(None, alias="cstIcms")
    aliquota_icms: Optional[Decimal] = Field(None, alias="aliquotaIcms")
    codigo_grupo: Optional[int] = Field(None, alias="codigoGrupo")
    nome_grupo: Optional[str] = Field(None, alias="nomeGrupo")
    sub_grupo_1_codigo: Optional[int] = Field(None, alias="subGrupo1Codigo")
    sub_grupo_2_codigo: Optional[int] = Field(None, alias="subGrupo2Codigo")
    sub_grupo_3_codigo: Optional[int] = Field(None, alias="subGrupo3Codigo")
    tipo_produto: Optional[str] = Field(None, alias="tipoProduto")
    tipo_combustivel: Optional[str] = Field(None, alias="tipoCombustivel")
    combustivel: bool = False

    @field_validator("preco_venda", "preco_custo", "estoque_atual", "aliquota_icms", mode="before")
    @classmethod
    def decimal_fields(cls, v):
        if v is None:
            return None
        return _d(v)

    @field_validator("ativo", mode="before")
    @classmethod
    def parse_ativo(cls, v):
        if v is None:
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in ("false", "n", "0", "inativo", "i"):
            return False
        return True


class PaginatedProdutosResponse(BaseModel):
    model_config = ConfigDict(serialize_by_alias=False)

    pagina_atual: int
    total_paginas: int
    total_registros: int
    produtos: List[WebPostoProdutoSchema]
    fonte: str = "webposto_integracao"
    cache_hit: bool = False
