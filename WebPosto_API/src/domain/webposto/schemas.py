"""
Modelos Pydantic v2 — respostas tipadas da API WebPosto (Swagger/Confluence).
Domínio puro: sem httpx, requests ou infraestrutura.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from src.domain.value_objects.payment_method import PaymentMethod


class FormaPagamentoTipo(str, Enum):
    PIX = "PIX"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    DINHEIRO = "DINHEIRO"
    PRAZO = "PRAZO"
    OUTRO = "OUTRO"


class FormaPagamento(BaseModel):
    """Consolidado por forma de pagamento (Pix / Cartão / Dinheiro)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    tipo: FormaPagamentoTipo
    valor: Decimal = Decimal("0")
    quantidade_transacoes: int = 0

    @classmethod
    def from_raw(cls, raw: str | None, valor: Decimal | float = 0, qtd: int = 0) -> "FormaPagamento":
        return cls(
            tipo=FormaPagamentoTipo(PaymentMethod.from_raw(raw).value),
            valor=Decimal(str(valor or 0)),
            quantidade_transacoes=qtd,
        )


class VendaCupomItem(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    produto_codigo: int = Field(alias="produtoCodigo")
    descricao: str = ""
    quantidade: Decimal = Decimal("0")
    valor_unitario: Decimal = Field(default=Decimal("0"), alias="valorUnitario")
    valor_total: Decimal = Field(default=Decimal("0"), alias="valorTotal")


class VendaCupom(BaseModel):
    """Cupom de venda — combustível e conveniência (últimas ~2h na consulta)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    venda_codigo: int = Field(alias="vendaCodigo")
    data_emissao: datetime
    filial_codigo: Optional[int] = Field(default=None, alias="filialCodigo")
    forma_pagamento: FormaPagamentoTipo = FormaPagamentoTipo.OUTRO
    valor_total: Decimal = Field(default=Decimal("0"), alias="valorTotal")
    itens: List[VendaCupomItem] = Field(default_factory=list)

    @classmethod
    def from_api_row(cls, row: dict) -> "VendaCupom":
        raw_fp = row.get("formaPagamento") or row.get("tipoPagamento")
        return cls(
            vendaCodigo=int(row.get("vendaCodigo") or row.get("codigo") or 0),
            data_emissao=_parse_dt(row.get("data") or row.get("dataEmissao")),
            filialCodigo=row.get("filialCodigo") or row.get("empresaCodigo"),
            forma_pagamento=FormaPagamentoTipo(PaymentMethod.from_raw(raw_fp).value),
            valorTotal=row.get("valorTotal") or row.get("valor") or 0,
            itens=[],
        )


class WebPostoVendaItem(BaseModel):
    """Contrato tolerante às variações conhecidas de VENDA_ITEM."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="allow")

    venda_codigo: int = Field(
        validation_alias=AliasChoices("vendaCodigo", "codigoVenda", "venda_codigo")
    )
    produto_codigo: int = Field(
        validation_alias=AliasChoices("produtoCodigo", "codigoProduto", "produto_codigo")
    )
    quantidade: Decimal = Decimal("0")
    valor_unitario: Decimal = Field(
        default=Decimal("0"),
        validation_alias=AliasChoices(
            "valorUnitario", "precoUnitario", "precoVenda", "valor_unitario"
        ),
    )
    valor_total: Decimal = Field(
        default=Decimal("0"),
        validation_alias=AliasChoices("valorTotal", "totalVenda", "valor", "valor_total"),
    )
    grupo_codigo: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("grupoCodigo", "codigoGrupo", "grupo_codigo"),
    )

    @field_validator("quantidade", "valor_unitario", "valor_total", mode="before")
    @classmethod
    def parse_decimal(cls, value) -> Decimal:
        return Decimal(str(value or 0))


class WebPostoVenda(BaseModel):
    """Contrato transacional mínimo de VENDA, sem fabricar campos ausentes."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="allow")

    venda_codigo: int = Field(
        validation_alias=AliasChoices("vendaCodigo", "codigo", "codigoVenda", "venda_codigo")
    )
    empresa_codigo: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("empresaCodigo", "filialCodigo", "empresa_codigo"),
    )
    data_emissao: Optional[datetime] = Field(
        default=None,
        validation_alias=AliasChoices(
            "dataEmissao", "dataHora", "data", "dataVenda", "data_emissao"
        ),
    )
    valor_total: Decimal = Field(
        default=Decimal("0"),
        validation_alias=AliasChoices("valorTotal", "totalVenda", "valor", "valor_total"),
    )

    @field_validator("valor_total", mode="before")
    @classmethod
    def parse_decimal(cls, value) -> Decimal:
        return Decimal(str(value or 0))


class WebPostoDespesa(BaseModel):
    """Contrato mínimo de despesa financeira retornada pelo WebPosto."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="allow")

    despesa_codigo: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices(
            "despesaCodigo", "codigo", "codigoDespesa", "despesa_codigo"
        ),
    )
    empresa_codigo: int = Field(
        validation_alias=AliasChoices("empresaCodigo", "filialCodigo", "empresa_codigo"),
    )
    data_movimento: Optional[datetime] = Field(
        default=None,
        validation_alias=AliasChoices(
            "dataMovimento", "dataEmissao", "data", "data_movimento"
        ),
    )
    descricao: str = ""
    valor: Decimal = Decimal("0")
    centro_custo_codigo: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices(
            "centroCustoCodigo", "codigoCentroCusto", "centro_custo_codigo"
        ),
    )
    plano_conta_gerencial_codigo: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices(
            "planoContaGerencialCodigo",
            "plano_conta_gerencial_codigo",
        ),
    )

    @field_validator("valor", mode="before")
    @classmethod
    def parse_decimal(cls, value) -> Decimal:
        return Decimal(str(value or 0))


class WebPostoMovimentoCaixa(BaseModel):
    """Contrato mínimo para entradas e saídas de caixa."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="allow")

    movimento_codigo: int = Field(
        validation_alias=AliasChoices(
            "movimentoCodigo",
            "caixaCodigo",
            "codigo",
            "codigoMovimento",
            "movimento_codigo",
        )
    )
    empresa_codigo: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("empresaCodigo", "filialCodigo", "empresa_codigo"),
    )
    data_movimento: Optional[datetime] = Field(
        default=None,
        validation_alias=AliasChoices("dataMovimento", "data", "data_movimento"),
    )
    tipo: str = ""
    descricao: str = ""
    valor: Decimal = Decimal("0")

    @field_validator("valor", mode="before")
    @classmethod
    def parse_decimal(cls, value) -> Decimal:
        return Decimal(str(value or 0))


class VolumeTanque(BaseModel):
    """Leitura física/lógica de tanque (Swagger ESTOQUE / tanques)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    tanque_codigo: int = Field(alias="tanqueCodigo")
    produto_codigo: Optional[int] = Field(default=None, alias="produtoCodigo")
    produto_nome: str = Field(default="", alias="nomeProduto")
    volume_litros: Decimal = Decimal("0")
    capacidade_litros: Optional[Decimal] = None
    medido_em: Optional[datetime] = None

    @classmethod
    def from_api_row(cls, row: dict) -> "VolumeTanque":
        litros = row.get("volume") or row.get("litros") or row.get("quantidade") or 0
        cap = row.get("capacidade") or row.get("capacidadeLitros")
        return cls(
            tanqueCodigo=int(row.get("tanqueCodigo") or row.get("codigo") or 0),
            produtoCodigo=row.get("produtoCodigo"),
            nomeProduto=str(row.get("nomeProduto") or row.get("nome") or ""),
            volume_litros=Decimal(str(litros)),
            capacidade_litros=Decimal(str(cap)) if cap is not None else None,
            medido_em=_parse_dt(row.get("dataMedicao") or row.get("medidoEm")),
        )


def _parse_dt(raw) -> datetime:
    if not raw:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:
        return datetime.utcnow()
