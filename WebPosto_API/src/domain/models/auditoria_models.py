"""
Modelos Pydantic para Auditoria de Postos
Integrado com WebPosto_API DDD Architecture
Estrutura de Despesas de Caixa e Fechamentos
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ============ ENUMS ============
class CategoriaDesapesa(str, Enum):
    LUZ = "luz"
    GELO = "gelo"
    VALE_OPERADOR = "vale_operador"
    VALE_CLIENTE = "vale_cliente"
    MANUTENCAO = "manutencao"
    COMBUSTIVEL = "combustivel"
    LIMPEZA = "limpeza"
    INSUMOS = "insumos"
    OUTROS = "outros"


class StatusJustificativa(str, Enum):
    PENDENTE = "pendente"
    JUSTIFICADA = "justificada"
    REJEITADA = "rejeitada"
    EM_ANALISE = "em_analise"


class TipoCaixa(str, Enum):
    PISTA = "pista"
    CONVENIENCIA = "conveniencia"
    RESTAURANTE = "restaurante"


class StatusCaixa(str, Enum):
    ABERTO = "aberto"
    FECHADO = "fechado"
    CONSOLIDADO = "consolidado"
    EM_AUDITORIA = "em_auditoria"


class EspecieFinanceira(str, Enum):
    DINHEIRO = "dinheiro"
    PIX = "pix"
    CARTAO_DEBITO = "cartao_debito"
    CARTAO_CREDITO = "cartao_credito"
    FROTISTA = "frotista"
    PRAZO = "prazo"


# ============ MODELS ============
class DespesaCaixa(BaseModel):
    """Representa uma despesa registrada no caixa"""

    id: str = Field(..., description="ID único da despesa")
    unidade_id: str = Field(..., description="ID da unidade (Real, Casa Caiada, VIP)")
    caixa_tipo: TipoCaixa = Field(..., description="Tipo de caixa")
    horario: datetime = Field(..., description="Horário da despesa")
    categoria: CategoriaDesapesa = Field(..., description="Categoria da despesa")
    valor: float = Field(..., gt=0, description="Valor da despesa")
    operador: str = Field(..., description="Operador que registrou")
    descricao: Optional[str] = Field(None, description="Descrição adicional")
    status_justificativa: StatusJustificativa = Field(
        default=StatusJustificativa.PENDENTE, description="Status da justificativa"
    )
    documento_anexo: Optional[str] = Field(
        None, description="URL/Path do documento comprobatório"
    )
    tem_documento: bool = Field(default=False, description="Flag: tem documento anexo?")

    @field_validator("valor")
    @classmethod
    def validar_valor(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Valor não pode ser negativo")
        return round(v, 2)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "exp_001",
                "unidade_id": "real_01",
                "caixa_tipo": "pista",
                "horario": "2026-04-12T14:30:00",
                "categoria": "gelo",
                "valor": 85.50,
                "operador": "João Silva",
                "status_justificativa": "justificada",
                "tem_documento": True,
            }
        }
    )


class MovimentacaoEspecie(BaseModel):
    """Movimentação de uma espécie financeira"""

    especie: EspecieFinanceira
    valor_esperado: float = Field(..., ge=0, description="Valor que deveria ter")
    valor_informado: float = Field(
        ..., ge=0, description="Valor informado pelo operador"
    )
    diferenca: float = Field(default=0, description="Diferença (esperado - informado)")
    variacao_percentual: float = Field(default=0, description="Variação %")

    @model_validator(mode="after")
    def calcular_diferenca_e_variacao(self) -> Self:
        diferenca = round(self.valor_esperado - self.valor_informado, 2)
        variacao = 0.0
        if self.valor_esperado > 0:
            variacao = round((diferenca / self.valor_esperado) * 100, 2)
        return self.model_copy(
            update={"diferenca": diferenca, "variacao_percentual": variacao}
        )


class FechamentoCaixa(BaseModel):
    """Fechamento consolidado de um caixa"""

    id: str = Field(..., description="ID único do fechamento")
    unidade_id: str = Field(..., description="ID da unidade")
    caixa_tipo: TipoCaixa = Field(..., description="Tipo de caixa")

    # Temporalidade
    horario_abertura: datetime = Field(..., description="Quando abriu")
    horario_fechamento: datetime = Field(..., description="Quando fechou")

    # Faturamento
    faturamento_bruto: float = Field(default=0, ge=0, description="Total vendido")
    despesas_caixa_total: float = Field(
        default=0, ge=0, description="Despesas da pista/conveniência"
    )

    # Movimentações por espécie
    movimentacoes: List[MovimentacaoEspecie] = Field(
        default_factory=list, description="Detalhamento por espécie"
    )

    # Saldos
    saldo_esperado_dinheiro: float = Field(
        default=0, description="Saldo esperado em dinheiro"
    )
    saldo_informado_dinheiro: float = Field(
        default=0, description="Saldo informado pelo operador"
    )
    quebra_caixa: float = Field(default=0, description="Diferença de caixa")

    # Status
    status: StatusCaixa = Field(
        default=StatusCaixa.ABERTO, description="Status do fechamento"
    )
    operador_fechamento: str = Field(..., description="Operador que fechou")

    # Auditoria
    flagged_auditoria: bool = Field(
        default=False, description="Marcado para auditoria?"
    )
    motivo_auditoria: Optional[str] = Field(None, description="Motivo da auditoria")
    despesas_sem_categoria: int = Field(
        default=0, description="Qtd despesas sem categoria"
    )
    despesas_sem_documento: int = Field(default=0, description="Qtd despesas sem anexo")

    @model_validator(mode="after")
    def calcular_quebra(self) -> Self:
        quebra = round(
            self.saldo_esperado_dinheiro - self.saldo_informado_dinheiro,
            2,
        )
        return self.model_copy(update={"quebra_caixa": quebra})

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "fech_001",
                "unidade_id": "real_01",
                "caixa_tipo": "pista",
                "horario_abertura": "2026-04-12T07:00:00",
                "horario_fechamento": "2026-04-12T23:00:00",
                "faturamento_bruto": 5420.50,
                "despesas_caixa_total": 250.00,
                "status": "fechado",
                "operador_fechamento": "Maria Santos",
            }
        }
    )


class ResumoAuditoriaUnidade(BaseModel):
    """Resumo consolidado de uma unidade para auditoria"""

    unidade_id: str
    data: datetime

    # KPIs
    faturamento_total: float = Field(default=0, description="Soma de todos caixas")
    despesas_operacionais: float = Field(default=0, description="Total despesas")
    saldo_especie_total: float = Field(default=0, description="Total em dinheiro")

    # Quebras
    quebra_total: float = Field(default=0, description="Quebra consolidada")
    quebra_percentual: float = Field(default=0, description="% quebra vs faturamento")

    # Status
    caixas_fechados: int = Field(default=0)
    caixas_abertos: int = Field(default=0)
    caixas_em_auditoria: int = Field(default=0)

    # Alertas
    despesas_sem_categoria_total: int = Field(default=0)
    despesas_sem_documento_total: int = Field(default=0)
    caixas_com_quebra_acima_10: int = Field(
        default=0, description="Caixas com quebra > R$10"
    )

    # Comparativo
    desvio_percentual_media_despesas: float = Field(
        default=0, description="Desvio % vs média histórica (5%)"
    )
    outlier_unidade: bool = Field(default=False, description="Unidade é outlier?")


class ListaFechamentos(BaseModel):
    """Container para lista de fechamentos do dia"""

    unidade_id: str
    data: datetime
    fechamentos: List[FechamentoCaixa] = Field(default_factory=list)
    total_caixas: int = Field(default=0)
    resumo: Optional[ResumoAuditoriaUnidade] = None
