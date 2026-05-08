"""Modelos Pydantic para validação de dados."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

# ============ Financeiro Models ============


class FechamentoCaixaItem(BaseModel):
    """Item individual de fechamento de caixa."""

    caixa_id: int = Field(..., description="ID do caixa")
    operador: str = Field(..., description="Nome do operador")
    horario_abertura: datetime = Field(..., description="Hora de abertura")
    horario_fechamento: Optional[datetime] = Field(
        None, description="Hora de fechamento"
    )
    faturamento_bruto: float = Field(..., description="Total vendido")
    despesas_caixa: float = Field(
        default=0.0, description="Despesas da pista/conveniência"
    )
    saldo_esperado: float = Field(..., description="Saldo esperado em caixa")
    saldo_informado: float = Field(..., description="Saldo informado pelo operador")
    quebra_caixa: float = Field(
        default=0.0, description="Diferença: esperado - informado"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "caixa_id": 1,
                "operador": "João Silva",
                "horario_abertura": "2026-04-12T10:00:00",
                "horario_fechamento": "2026-04-12T22:00:00",
                "faturamento_bruto": 5000.50,
                "despesas_caixa": 250.00,
                "saldo_esperado": 4750.50,
                "saldo_informado": 4740.00,
                "quebra_caixa": 10.50,
            }
        }
    )


class DespesaCaixa(BaseModel):
    """Despesa registrada no caixa."""

    id: int = Field(..., description="ID da despesa")
    horario: datetime = Field(..., description="Horário da despesa")
    categoria: str = Field(..., description="Categoria (Luz, Gelo, Vales, etc)")
    valor: float = Field(..., description="Valor da despesa")
    operador: str = Field(..., description="Quem registrou")
    justificativa: Optional[str] = Field(None, description="Motivo da despesa")
    documento_anexado: bool = Field(default=False, description="Comprovante anexado?")
    status: str = Field(default="pendente", description="Status de validação")


class FechamentoCaixaResponse(BaseModel):
    """Resposta completa de fechamento."""

    sucesso: bool = Field(..., description="Sucesso da operação")
    unidade: str = Field(..., description="Nome da unidade")
    data: datetime = Field(..., description="Data do fechamento")
    caixas: List[FechamentoCaixaItem] = Field(default_factory=list)
    despesas: List[DespesaCaixa] = Field(default_factory=list)
    faturamento_total: float = Field(default=0.0)
    despesas_total: float = Field(default=0.0)
    saldo_especie: float = Field(default=0.0)
    quebra_total: float = Field(default=0.0)


# ============ Movimentação por Espécie ============


class MovimentacaoEspecie(BaseModel):
    """Movimentação por tipo de pagamento."""

    modalidade: str = Field(..., description="Dinheiro, PIX, Débito, Crédito, etc")
    valor_sistematico: float = Field(..., description="Valor no sistema")
    valor_informado: float = Field(..., description="Valor que operador informou")
    diferenca: float = Field(..., description="Desvio: sistematico - informado")
    percentual_desvio: float = Field(default=0.0, description="Percentual de desvio")


# ============ Insights de Auditoria ============


class InsightAuditor(BaseModel):
    """Insight automático da auditoria estoica."""

    tipo: str = Field(..., description="tipo_alerta, anomalia_padrão, oportunidade")
    severidade: str = Field(..., description="info, warning, crítico")
    mensagem: str = Field(..., description="Descrição do insight")
    unidade_comparada: Optional[str] = Field(None, description="Unidade comparada")
    metrica: Optional[str] = Field(None, description="Métrica relevante")
    desvio_percentual: Optional[float] = Field(None, description="Desvio em %")
