from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlmodel import Field, SQLModel


class GrupoRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(index=True, unique=True)
    ativo: bool = Field(default=True)


class SubgrupoRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    grupo_id: int = Field(foreign_key="gruporecord.id", index=True)
    nome: str = Field(index=True)
    ativo: bool = Field(default=True)


class ProdutoRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subgrupo_id: int = Field(foreign_key="subgruporecord.id", index=True)
    sku: Optional[str] = Field(default=None, index=True, unique=True)
    nome: str = Field(index=True)
    preco: Decimal = Field(default=Decimal("0.00"), max_digits=14, decimal_places=2)
    preco_custo: Decimal = Field(default=Decimal("0.00"), max_digits=14, decimal_places=2)
    ativo: bool = Field(default=True)


class MovimentacaoCaixaRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    posto_id: str = Field(index=True)
    tipo: str = Field(index=True)
    valor: Decimal = Field(default=Decimal("0.00"), max_digits=14, decimal_places=2)
    descricao: Optional[str] = None
    data_movimento: datetime = Field(default_factory=datetime.utcnow, index=True)


class NfeCompraRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    numero_nfe: str = Field(index=True, unique=True)
    fornecedor: str = Field(index=True)
    valor_total: Decimal = Field(default=Decimal("0.00"), max_digits=14, decimal_places=2)
    data_emissao: datetime = Field(default_factory=datetime.utcnow, index=True)
    status: str = Field(default="aberta", index=True)


class ContaPagarRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    descricao: str
    fornecedor: Optional[str] = Field(default=None, index=True)
    valor: Decimal = Field(default=Decimal("0.00"), max_digits=14, decimal_places=2)
    vencimento: datetime = Field(index=True)
    status: str = Field(default="aberta", index=True)


class TituloReceberRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    descricao: str
    cliente: Optional[str] = Field(default=None, index=True)
    valor: Decimal = Field(default=Decimal("0.00"), max_digits=14, decimal_places=2)
    vencimento: datetime = Field(index=True)
    status: str = Field(default="aberto", index=True)


class CartaoReceberRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bandeira: str = Field(index=True)
    nsu: Optional[str] = Field(default=None, index=True)
    valor: Decimal = Field(default=Decimal("0.00"), max_digits=14, decimal_places=2)
    data_prevista: datetime = Field(index=True)
    status: str = Field(default="pendente", index=True)
