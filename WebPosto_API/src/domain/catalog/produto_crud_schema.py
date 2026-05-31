"""Schemas CRUD de produtos — alinhados a IntegracaoProdutoCadastro (API Quality)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.catalog.product_schema import WebPostoProdutoSchema


class ProdutoTributoIcmsIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    percentual_icms_saida: float = Field(0, alias="percentualIcmsSaida")
    cst_saida: str = Field("060", alias="cstSaida", max_length=3)
    percentual_icms_entrada: float = Field(0, alias="percentualIcmsEntrada")
    cst_entrada: str = Field("060", alias="cstEntrada", max_length=3)


class ProdutoTributoPisCofinsIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cst_pis_saida: str = Field("01", alias="cstPisSaida", max_length=2)
    cst_cofins_saida: str = Field("01", alias="cstCofinsSaida", max_length=2)


class ProdutoCreateRequest(BaseModel):
    """POST /INTEGRACAO/INCLUIR_PRODUTO ou POST /INTEGRACAO/PRODUTO."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    descricao: str = Field(..., min_length=1, max_length=120)
    descricao_resumida: Optional[str] = Field(None, alias="descricaoResumida")
    tipo_produto: str = Field("P", alias="tipoProduto", description="C|P|U|I|O|S|K|8")
    grupo_codigo: int = Field(..., alias="grupoCodigo")
    codigo_externo: Optional[str] = Field(None, alias="codigoExterno")
    unidade_compra: str = Field("UN", alias="unidadeCompra", max_length=6)
    unidade_venda: str = Field("UN", alias="unidadeVenda", max_length=6)
    preco_custo: Decimal = Field(Decimal("0"), alias="precoCusto", ge=0)
    preco_compra: Decimal = Field(Decimal("0"), alias="precoCompra", ge=0)
    preco_venda: Decimal = Field(..., alias="precoVenda", ge=0)
    codigo_barras: Optional[str] = Field(None, alias="codigoBarras")
    codigo_ncm: str = Field("00000000", alias="codigoNcm", max_length=8)
    codigo_cest: Optional[str] = Field(None, alias="codigoCest", max_length=7)
    ativo: bool = True
    iat: str = Field("A", description="A=Arredondamento, T=Truncamento")
    ippt: str = Field("T", description="P=Própria, T=Terceiro")
    permite_venda_estoque_negativo: bool = Field(False, alias="permiteVendaEstoqueNegativo")
    produto_vende_fracionado: bool = Field(False, alias="produtoVendeFracionado")
    utiliza_codigo_barras: bool = Field(True, alias="utilizaCodigoBarras")
    tributacao_monofasica: Optional[float] = Field(None, alias="tributacaoMonofasica")
    tributo_icms: Optional[ProdutoTributoIcmsIn] = Field(None, alias="tributoIcms")
    tributo_pis_cofins: Optional[ProdutoTributoPisCofinsIn] = Field(
        None, alias="tributoPisCofins"
    )


class ProdutoUpdateRequest(BaseModel):
    """PUT /INTEGRACAO/ALTERAR_PRODUTO/{id} — mesmos campos do cadastro."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    descricao: Optional[str] = None
    descricao_resumida: Optional[str] = Field(None, alias="descricaoResumida")
    tipo_produto: Optional[str] = Field(None, alias="tipoProduto")
    grupo_codigo: Optional[int] = Field(None, alias="grupoCodigo")
    unidade_compra: Optional[str] = Field(None, alias="unidadeCompra")
    unidade_venda: Optional[str] = Field(None, alias="unidadeVenda")
    preco_custo: Optional[Decimal] = Field(None, alias="precoCusto")
    preco_compra: Optional[Decimal] = Field(None, alias="precoCompra")
    preco_venda: Optional[Decimal] = Field(None, alias="precoVenda")
    codigo_barras: Optional[str] = Field(None, alias="codigoBarras")
    codigo_ncm: Optional[str] = Field(None, alias="codigoNcm")
    codigo_cest: Optional[str] = Field(None, alias="codigoCest")
    ativo: Optional[bool] = None
    tributo_icms: Optional[ProdutoTributoIcmsIn] = Field(None, alias="tributoIcms")
    tributo_pis_cofins: Optional[ProdutoTributoPisCofinsIn] = Field(
        None, alias="tributoPisCofins"
    )


class ProdutoCrudResponse(BaseModel):
    ok: bool = True
    produto: Optional[WebPostoProdutoSchema] = None
    raw: Optional[Any] = None
    mensagem: Optional[str] = None
    endpoint: Optional[str] = None
