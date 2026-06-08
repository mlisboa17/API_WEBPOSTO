"""
Modelos de dados para webPosto API.
Validação rigorosa com Pydantic v2.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


# ===============================================
# ENUMS
# ===============================================


class TipoTitulo(str, Enum):
    """Tipos de título financeiro."""

    RECEBER = "RECEBER"
    PAGAR = "PAGAR"


class StatusTitulo(str, Enum):
    """Status de um título."""

    PENDENTE = "pendente"
    PAGO = "pago"
    VENCIDO = "vencido"
    CANCELADO = "cancelado"


class TipoMovimentoCaixa(str, Enum):
    """Tipos de movimento de caixa."""

    ABERTURA = "ABERTURA"
    VENDA = "VENDA"
    SAQUE = "SAQUE"
    FECHAMENTO = "FECHAMENTO"
    TRANSFERENCIA = "TRANSFERENCIA"
    DEVOLUCAO = "DEVOLUCAO"
    AJUSTE = "AJUSTE"


# ===============================================
# MODELOS DE ENTRADA (Request)
# ===============================================


class FinanceiroCreate(BaseModel):
    """Criar novo título."""

    model_config = ConfigDict(str_strip_whitespace=True)

    tipo: TipoTitulo
    valor: float = Field(gt=0, description="Valor deve ser positivo")
    data_vencimento: datetime
    descricao: str = Field(min_length=3, max_length=255)
    cliente_fornecedor: str = Field(min_length=3, max_length=255)
    categoria: Optional[str] = None


class FinanceiroUpdate(BaseModel):
    """Atualizar título existente."""

    model_config = ConfigDict(str_strip_whitespace=True)

    tipo: Optional[TipoTitulo] = None
    valor: Optional[float] = Field(None, gt=0)
    data_vencimento: Optional[datetime] = None
    descricao: Optional[str] = Field(None, min_length=3, max_length=255)
    cliente_fornecedor: Optional[str] = Field(None, min_length=3, max_length=255)
    categoria: Optional[str] = None
    pago: Optional[bool] = None
    data_pagamento: Optional[datetime] = None


class CaixaCreate(BaseModel):
    """Criar novo movimento de caixa."""

    model_config = ConfigDict(str_strip_whitespace=True)

    numero_caixa: int = Field(ge=1, le=999)
    descricao: str = Field(min_length=3, max_length=255)
    tipo_movimento: TipoMovimentoCaixa
    valor: float = Field(gt=0, description="Valor deve ser positivo")
    referencia: Optional[str] = Field(None, max_length=50)
    operador: Optional[str] = Field(None, max_length=100)


class CaixaUpdate(BaseModel):
    """Atualizar movimento de caixa."""

    model_config = ConfigDict(str_strip_whitespace=True)

    numero_caixa: Optional[int] = Field(None, ge=1, le=999)
    descricao: Optional[str] = Field(None, min_length=3, max_length=255)
    tipo_movimento: Optional[TipoMovimentoCaixa] = None
    valor: Optional[float] = Field(None, gt=0)
    referencia: Optional[str] = Field(None, max_length=50)
    operador: Optional[str] = Field(None, max_length=100)


# ===============================================
# MODELOS DE SAÍDA (Response)
# ===============================================


class FinanceiroResponse(BaseModel):
    """Resposta de título financeiro."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tipo: TipoTitulo
    valor: float
    data_vencimento: datetime
    descricao: str
    cliente_fornecedor: str
    categoria: Optional[str] = None
    pago: bool = False
    dias_vencido: int
    status: StatusTitulo
    webposto_id: Optional[str] = None
    data_criacao: datetime
    data_pagamento: Optional[datetime] = None
    data_atualizacao: datetime
    modificado_por: Optional[str] = None


class CaixaResponse(BaseModel):
    """Resposta de movimento de caixa."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    numero_caixa: int
    descricao: str
    tipo_movimento: TipoMovimentoCaixa
    valor: float
    saldo: float
    data_movimento: datetime
    referencia: Optional[str] = None
    operador: Optional[str] = None
    webposto_id: Optional[str] = None
    data_criacao: datetime
    data_atualizacao: datetime
    modificado_por: Optional[str] = None


class AuditoriaResponse(BaseModel):
    """Log de auditoria."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tabela: str  # 'financeiro' ou 'caixa'
    record_id: str
    operacao: Literal["CREATE", "UPDATE", "DELETE"]
    usuario: str
    valores_antes: Optional[dict] = None
    valores_depois: Optional[dict] = None
    data_operacao: datetime
    ip_origem: Optional[str] = None
    motivo: Optional[str] = None


# ===============================================
# MODELOS DE RESPOSTA GLOBAL
# ===============================================


class APIResponse(BaseModel):
    """Resposta genérica da API."""

    status: Literal["success", "error", "warning"]
    mensagem: str
    dados: Optional[dict | list] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: Optional[str] = None


class PaginationParams(BaseModel):
    """Parâmetros de paginação."""

    pagina: int = Field(1, ge=1)
    limite: int = Field(50, ge=1, le=500)
    ordenar_por: Optional[str] = None
    ordenacao: Literal["asc", "desc"] = "desc"


class ListaResponse(BaseModel):
    """Resposta com lista paginada."""

    status: Literal["success", "error"]
    total: int
    pagina: int
    limite: int
    total_paginas: int
    dados: list
    timestamp: datetime = Field(default_factory=datetime.utcnow)
