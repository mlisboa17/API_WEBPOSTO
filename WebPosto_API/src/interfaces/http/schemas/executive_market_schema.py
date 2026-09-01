from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

class CompetitorPriceCreate(BaseModel):
    concorrente_nome: str
    produto_codigo: str
    produto_nome: str
    preco_venda_rs: float
    datahora: str
    unidade_codigo: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class CompetitorPrice(CompetitorPriceCreate):
    id: int

class ProductBenchmark(BaseModel):
    produto_codigo: str
    produto_nome: str
    preco_lisboa_rs: float
    preco_medio_concorrentes_rs: float
    preco_minimo_concorrentes_rs: float
    preco_maximo_concorrentes_rs: float
    spread_rs: float = Field(description="Diferença Lisboa vs média concorrentes")
    margem_lisboa_rs: float = Field(description="Margem praticada na Lisboa (preço - custo médio)")
    squeeze_risk: bool = Field(description="True quando concorrente reduz preço e margem Lisboa cai abaixo do limite")

class MarketBenchmarkSummary(BaseModel):
    produtos: List[ProductBenchmark]
    margem_minima_configurada_pct: float
    alertas_squeeze: List[str]
    model_config = ConfigDict(frozen=True)
