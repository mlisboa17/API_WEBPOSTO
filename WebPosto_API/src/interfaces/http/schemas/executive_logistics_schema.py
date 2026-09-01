from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class LogisticsSupplierEfficiency(BaseModel):
    fornecedor: str
    custo_frete_medio_rs_litro: float
    markup_logistico_pct: float
    delta_fob_cif_rs_litro: float
    total_litros_comprados: float


class LogisticsSummary(BaseModel):
    custo_frete_efetivo_total_rs: float
    frete_medio_grupo_rs_litro: float
    custo_oportunidade_frete_total_rs: float
    eficiencia_por_fornecedor: List[LogisticsSupplierEfficiency]
    fonte: str = "Dado Real - Fonte NF webPosto"
    notas_com_frete: int = 0
    detalhe_fonte: Optional[str] = None
    model_config = ConfigDict(frozen=True)
