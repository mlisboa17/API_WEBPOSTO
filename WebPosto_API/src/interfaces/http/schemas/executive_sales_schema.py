from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class HourlyVolume(BaseModel):
    hora: int
    litros: float
    ticket_medio: float


class SalesHeatmap(BaseModel):
    data: Dict[int, List[HourlyVolume]]


class PriceElasticityPoint(BaseModel):
    data: str
    preco_bomba_rs: float
    volume_litros: float
    margem_bruta_rs: float


class CrossSellingCombo(BaseModel):
    produtos: List[str]
    frequencia_conjunta_pct: float
    ticket_medio_combo: float
    margem_contribuicao_total_rs: float
    lift: float


class CompositionItem(BaseModel):
    categoria: str
    litros: float = 0.0
    faturamento_rs: float = 0.0
    margem_rs: float = 0.0
    participacao_pct: float = 0.0


class SectorShare(BaseModel):
    setor: str
    faturamento_rs: float
    participacao_pct: float


class SalesComposition(BaseModel):
    combustiveis: List[CompositionItem] = Field(default_factory=list)
    produtos_pista: List[CompositionItem] = Field(default_factory=list)
    conveniencia: List[CompositionItem] = Field(default_factory=list)
    participacao_setores: List[SectorShare] = Field(default_factory=list)
    penetracao_cross_selling_pct: float = 0.0
    faturamento_total_rs: float = 0.0
    empresa_codigo: Optional[int] = None


class BicoPerformance(BaseModel):
    bico: int = 0
    bomba: str = ""
    produto: str = ""
    litros: float = 0.0
    abastecimentos: int = 0
    faturamento: float = 0.0
    empresa_codigo: Optional[int] = None


class SalesAnalyticsSummary(BaseModel):
    heatmap: SalesHeatmap
    elasticidade: List[PriceElasticityPoint]
    coeficiente_elasticidade: float
    cesta_afinidade: List[CrossSellingCombo]
    taxa_conversao_pista_loja_pct: float
    volume_medio_diario_litros: float = Field(
        default=0.0,
        description="Volume médio diário em litros (dias com movimentação)",
    )
    composicao: SalesComposition = Field(default_factory=SalesComposition)
    performance_bicos: List[BicoPerformance] = Field(default_factory=list)
    model_config = ConfigDict(frozen=True)


# --- Inteligência Integrada de Cross-Selling (contrato camelCase) ---


class CompositionSummaryKPI(BaseModel):
    faturamentoTotal: float = 0.0
    faturamentoCombustivel: float = 0.0
    faturamentoProdutosPista: float = 0.0
    faturamentoConveniencia: float = 0.0
    litrosVendidos: float = 0.0
    quantidadeAbastecimentos: int = 0
    clientesLoja: int = 0
    ticketMedioAbastecimento: float = 0.0
    receitaNaoCombustivelPorAbastecimento: float = 0.0
    litrosPorAbastecimento: float = 0.0
    penetracaoProdutosPistaPercentual: float = 0.0
    penetracaoConvenienciaPercentual: float = 0.0
    penetracaoCrossSellingPercentual: float = 0.0


class CompositionBySectorItem(BaseModel):
    setor: str
    faturamento: float = 0.0
    margem: float = 0.0
    participacao: float = 0.0


class CrossSellingFunnel(BaseModel):
    totalAbastecimentos: int = 0
    clientesLoja: int = 0
    transacoesCombustivelProdutoPista: int = 0
    transacoesCombustivelConveniencia: int = 0
    transacoesCombustivelComboTotal: int = 0
    penetracaoProdutosPistaPercentual: float = 0.0
    penetracaoConvenienciaPercentual: float = 0.0
    penetracaoTotalPercentual: float = 0.0
    relacaoLojaPistaPercentual: float = 0.0


class FuelBreakdownItem(BaseModel):
    categoria: str
    litros: float = 0.0
    faturamento: float = 0.0
    participacao: float = 0.0


class SalesCompositionResponse(BaseModel):
    summary: CompositionSummaryKPI = Field(default_factory=CompositionSummaryKPI)
    compositionBySector: List[CompositionBySectorItem] = Field(default_factory=list)
    crossSellingFunnel: CrossSellingFunnel = Field(default_factory=CrossSellingFunnel)
    combustiveis: List[FuelBreakdownItem] = Field(default_factory=list)
    produtosPista: List[FuelBreakdownItem] = Field(default_factory=list)
    conveniencia: List[FuelBreakdownItem] = Field(default_factory=list)
    empresaCodigo: Optional[int] = None
    periodo: Dict[str, str] = Field(default_factory=dict)
    fonteAbastecimentos: str = "INTEGRACAO/ABASTECIMENTO"
    fallback: bool = False
    mensagem: Optional[str] = None
    model_config = ConfigDict(frozen=True)
