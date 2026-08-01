from __future__ import annotations
from typing import List, Dict
from pydantic import BaseModel, ConfigDict

class UnitLiquidity(BaseModel):
    unit_id: int
    unit_name: str
    saldo_bancario_rs: float
    contas_a_pagar_48h_rs: float
    necessidade_imediata_rs: float

class SweepSuggestion(BaseModel):
    origem_unit_id: int
    origem_name: str
    destino_unit_id: int
    destino_name: str
    valor_sugerido_rs: float
    justificativa: str

class TreasurySummary(BaseModel):
    saldo_consolidado_disponivel_rs: float
    exposicao_cheque_especial_total_rs: float
    aging_disponibilidade_caixa_dias: float
    liquidez_por_unidade: List[UnitLiquidity]
    sugestoes_sweep: List[SweepSuggestion]
    model_config = ConfigDict(frozen=True)
