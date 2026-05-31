"""Entidades e VOs de auditoria de caixa — domínio puro (sem httpx)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SubCentroCusto(str, Enum):
    """
    Sub-centros operacionais usados na auditoria.
    O posto pode ter 4 centros no cadastro WebPosto; usamos apenas estes 3.
    """

    PISTA = "PISTA"
    LOJA = "LOJA"
    FOOD = "FOOD"

    @classmethod
    def operacionais(cls) -> tuple["SubCentroCusto", ...]:
        return (cls.PISTA, cls.LOJA, cls.FOOD)

    @classmethod
    def from_legacy(cls, raw: str | None) -> "SubCentroCusto":
        u = (raw or "PISTA").strip().upper()
        if u in ("LOJA", "CONVENIENCIA", "CONVENIÊNCIA", "CONVENIENCE", "PDV", "LOJA_CONV"):
            return cls.LOJA
        if u in ("FOOD", "RESTAURANTE", "LANCHONETE", "LANCH", "REFEICAO", "REFEIÇÃO"):
            return cls.FOOD
        # 4º centro do ERP (admin/geral/outros) → não usado; mapeia para PISTA só se legado genérico
        if u in ("ADMIN", "GERAL", "OUTROS", "OUTRO", "MATRIZ"):
            return cls.PISTA
        return cls.PISTA


def calcular_faturamento_periodo(
    sub_centro: SubCentroCusto,
    vendas: List["AuditVendaLinha"],
) -> Decimal:
    """
    Faturamento do período em R$ — obrigatório para PISTA, LOJA e FOOD.
    PISTA: soma vendas combustível (ABASTECIMENTO).
    LOJA/FOOD: soma itens PDV filtrados por categoria.
    """
    total = sum((v.faturamento for v in vendas), Decimal("0"))
    return total.quantize(Decimal("0.01"))


class AuditTurno(BaseModel):
    model_config = ConfigDict(frozen=True)

    turno_id: str
    data: Optional[date] = None
    valor_caixa: Decimal = Decimal("0")
    valor_sistema: Decimal = Decimal("0")
    sub_centro: SubCentroCusto = SubCentroCusto.PISTA

    @field_validator("valor_caixa", "valor_sistema", mode="before")
    @classmethod
    def _dec(cls, v):
        return Decimal(str(v or 0)).quantize(Decimal("0.01"))


class AuditVendaLinha(BaseModel):
    model_config = ConfigDict(frozen=True)

    produto_codigo: str = ""
    categoria: str = ""
    litros: Decimal = Decimal("0")
    faturamento: Decimal = Decimal("0")

    @field_validator("litros", mode="before")
    @classmethod
    def _dec_litros(cls, v):
        return Decimal(str(v or 0)).quantize(Decimal("0.0001"))

    @field_validator("faturamento", mode="before")
    @classmethod
    def _dec_fat(cls, v):
        return Decimal(str(v or 0)).quantize(Decimal("0.01"))


class AuditDespesa(BaseModel):
    model_config = ConfigDict(frozen=True)

    descricao: str = ""
    plano_conta: str = ""
    valor: Decimal = Decimal("0")
    sub_centro: SubCentroCusto = SubCentroCusto.PISTA

    @field_validator("valor", mode="before")
    @classmethod
    def _dec(cls, v):
        return Decimal(str(v or 0)).quantize(Decimal("0.01"))


class AuditRawData(BaseModel):
    """Payload normalizado vindo do webPosto (ACL)."""

    model_config = ConfigDict(frozen=True)

    posto_id: str = "default"
    sub_centro: SubCentroCusto
    data_inicio: date
    data_fim: date
    turnos: List[AuditTurno] = Field(default_factory=list)
    vendas: List[AuditVendaLinha] = Field(default_factory=list)
    despesas: List[AuditDespesa] = Field(default_factory=list)
    caixa_apurado_total: Decimal = Decimal("0")
    caixa_apresentado_total: Decimal = Decimal("0")
    faturamento_periodo: Decimal = Decimal("0")


class FaturamentoSubCentro(BaseModel):
    """Faturamento consolidado em R$ para um sub-centro no período."""

    model_config = ConfigDict(frozen=True)

    sub_centro: SubCentroCusto
    faturamento_periodo: Decimal = Decimal("0")
    galonagem_litros: Decimal = Decimal("0")
    moeda: str = "BRL"

    @field_validator("faturamento_periodo", "galonagem_litros", mode="before")
    @classmethod
    def _dec(cls, v):
        return Decimal(str(v or 0)).quantize(Decimal("0.01"))


class FaturamentoConsolidadoResponse(BaseModel):
    """Resposta com os 3 sub-centros operacionais."""

    data_inicio: date
    data_fim: date
    posto_id: str = "default"
    itens: List[FaturamentoSubCentro] = Field(default_factory=list)
    faturamento_total_posto: Decimal = Decimal("0")

    @field_validator("faturamento_total_posto", mode="before")
    @classmethod
    def _dec(cls, v):
        return Decimal(str(v or 0)).quantize(Decimal("0.01"))


class AuditSession(BaseModel):
    """Resultado da reconciliação."""

    model_config = ConfigDict(frozen=True)

    job_id: Optional[str] = None
    posto_id: str = "default"
    sub_centro: SubCentroCusto
    data_inicio: date
    data_fim: date
    galonagem_litros: Decimal = Decimal("0")
    faturamento_periodo: Decimal = Decimal("0")
    moeda: str = "BRL"
    valor_apurado: Decimal = Decimal("0")
    valor_apresentado: Decimal = Decimal("0")
    divergencia: Decimal = Decimal("0")
    despesas_periodo: Decimal = Decimal("0")
    turnos_totais: int = 0
    alerta_critico: bool = False
    mensagem_alerta: Optional[str] = None
    processado_em: datetime = Field(default_factory=datetime.utcnow)
    cache_hit: bool = False

    @field_validator(
        "galonagem_litros",
        "faturamento_periodo",
        "valor_apurado",
        "valor_apresentado",
        "divergencia",
        "despesas_periodo",
        mode="before",
    )
    @classmethod
    def _dec(cls, v):
        return Decimal(str(v or 0)).quantize(Decimal("0.01"))
