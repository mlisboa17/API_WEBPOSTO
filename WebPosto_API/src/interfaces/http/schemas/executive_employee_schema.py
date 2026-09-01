from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

class EmployeeRanking(BaseModel):
    funcionario_codigo: int
    nome: str
    funcao: str
    litros_vendidos: float
    ticket_medio: float
    conversion_pct: float = Field(description="Percentual de conversão Gasolina Aditivada / Lubrificantes")
    galonagem_por_hora: float = Field(description="Litros vendidos por hora trabalhada")
    score: float = Field(description="Score de produtividade composto 0-100")

class CashBreakByEmployee(BaseModel):
    funcionario_codigo: int
    nome: str
    turno: str
    pdv_codigo: int
    caixa_codigo: int
    datahora: str
    diferenca: float = Field(description="Sobra/falta no fechamento do caixa")
    status: str

class EmployeePerformanceSummary(BaseModel):
    ranking: List[EmployeeRanking]
    auditoria_caixa: List[CashBreakByEmployee]
    media_galonagem_por_hora: float
    melhor_frentista: Optional[EmployeeRanking] = None
    pior_frentista: Optional[EmployeeRanking] = None
    model_config = ConfigDict(frozen=True)
