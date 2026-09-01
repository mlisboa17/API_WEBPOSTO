from __future__ import annotations
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query

from src.interfaces.http.authz import require_roles
from src.services.sales_analytics_service import SalesAnalyticsService
from src.services.sales_composition_service import SalesCompositionService
from src.services.logistics_freight_service import LogisticsFreightService
from src.services.treasury_consolidation_service import TreasuryConsolidationService
from src.services.elasticity_simulator_service import ElasticitySimulatorService
from src.services.executive_briefing_service import ExecutiveBriefingService
from src.utils.filial_normalizer import resolve_empresa_codigo
from src.services.webposto.offline_mode import (
    WebPostoOfflineBlocked,
    annotate_offline_success,
    classify_local_source,
    offline_unavailable_response,
    webposto_offline_mode,
)

from src.interfaces.http.schemas.executive_sales_schema import SalesAnalyticsSummary
from src.interfaces.http.schemas.executive_logistics_schema import LogisticsSummary
from src.interfaces.http.schemas.executive_treasury_schema import TreasurySummary

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive",
    tags=["Executive Analytics S52"],
)

_sales_service = SalesAnalyticsService()
_composition_service = SalesCompositionService()
_logistics_service = LogisticsFreightService()
_treasury_service = TreasuryConsolidationService()
_elasticity_service = ElasticitySimulatorService()
_briefing_service = ExecutiveBriefingService()

@router.get("/briefing", response_model=dict)
async def get_executive_briefing(
    dataReferencia: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: Optional[int] = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
):
    """Três destaques automáticos do D-1 para o cockpit da diretoria."""
    try:
        empresa = resolve_empresa_codigo(empresaCodigo)
        data = await _briefing_service.build(dataReferencia, empresa)
        body = {"success": True, "data": data, "namespace": "executive"}
        if webposto_offline_mode():
            return annotate_offline_success(body, source="cache_local")
        return body
    except WebPostoOfflineBlocked:
        return offline_unavailable_response(route="/api/v1/executive/briefing")
    except Exception as e:
        if webposto_offline_mode():
            return offline_unavailable_response(route="/api/v1/executive/briefing")
        logger.exception("briefing: %s", e)
        return {"success": False, "error": str(e)}


@router.get("/sales/analytics", response_model=dict)
async def get_sales_analytics(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: Optional[int] = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
):
    """
    Retorna heatmap de vendas, elasticidade e cesta de afinidade.
    """
    try:
        empresa = resolve_empresa_codigo(empresaCodigo)
        data = await _sales_service.analyze(dataInicial, dataFinal, empresa)
        payload = data.model_dump() if hasattr(data, "model_dump") else data
        return {"success": True, "data": payload, "namespace": "executive"}
    except Exception as e:
        logger.error(f"Erro em sales analytics: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/sales/composition", response_model=dict)
async def get_sales_composition(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: Optional[int] = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
):
    """
    Inteligência de composição e cross-selling (Pista x Lubrificantes x Conveniência).

    quantidadeAbastecimentos = COUNT(DISTINCT abastecimentoCodigo) via /INTEGRACAO/ABASTECIMENTO.
    Nunca usa contagem de notas fiscais.
    """
    try:
        empresa = resolve_empresa_codigo(empresaCodigo)
        data = await _composition_service.build(dataInicial, dataFinal, empresa)
        payload = data.model_dump() if hasattr(data, "model_dump") else data
        body = {"success": True, "data": payload, "namespace": "executive"}
        if webposto_offline_mode():
            fonte = ""
            if isinstance(payload, dict):
                fonte = str(payload.get("fonteAbastecimentos") or "")
            else:
                fonte = str(getattr(data, "fonteAbastecimentos", "") or "")
            return annotate_offline_success(body, source=classify_local_source(fonte))
        return body
    except WebPostoOfflineBlocked:
        return offline_unavailable_response(route="/api/v1/executive/sales/composition")
    except Exception as e:
        if webposto_offline_mode():
            return offline_unavailable_response(route="/api/v1/executive/sales/composition")
        logger.exception("Erro em sales composition: %s", e)
        return {
            "success": True,
            "data": {
                "summary": {
                    "faturamentoTotal": 0,
                    "faturamentoCombustivel": 0,
                    "faturamentoProdutosPista": 0,
                    "faturamentoConveniencia": 0,
                    "litrosVendidos": 0,
                    "quantidadeAbastecimentos": 0,
                    "clientesLoja": 0,
                    "ticketMedioAbastecimento": 0,
                    "receitaNaoCombustivelPorAbastecimento": 0,
                    "litrosPorAbastecimento": 0,
                    "penetracaoProdutosPistaPercentual": 0,
                    "penetracaoConvenienciaPercentual": 0,
                    "penetracaoCrossSellingPercentual": 0,
                },
                "compositionBySector": [
                    {"setor": "Combustíveis", "faturamento": 0, "margem": 0, "participacao": 0},
                    {"setor": "Produtos de Pista", "faturamento": 0, "margem": 0, "participacao": 0},
                    {"setor": "Conveniência", "faturamento": 0, "margem": 0, "participacao": 0},
                ],
                "crossSellingFunnel": {
                    "totalAbastecimentos": 0,
                    "clientesLoja": 0,
                    "transacoesCombustivelProdutoPista": 0,
                    "transacoesCombustivelConveniencia": 0,
                    "transacoesCombustivelComboTotal": 0,
                    "penetracaoProdutosPistaPercentual": 0,
                    "penetracaoConvenienciaPercentual": 0,
                    "penetracaoTotalPercentual": 0,
                    "relacaoLojaPistaPercentual": 0,
                },
                "combustiveis": [],
                "produtosPista": [],
                "conveniencia": [],
                "empresaCodigo": empresaCodigo,
                "periodo": {"inicio": dataInicial, "fim": dataFinal},
                "fonteAbastecimentos": "INTEGRACAO/ABASTECIMENTO",
                "fallback": True,
                "mensagem": str(e),
            },
            "namespace": "executive",
        }

@router.get("/sales/elasticity-products", response_model=dict)
async def get_elasticity_products(
    empresaCodigo: Optional[int] = Query(None),
    days: int = Query(90, ge=7, le=180),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
):
    """Catálogo de combustíveis do histórico local (sales_daily_summary) p/ simulador."""
    try:
        data = await _elasticity_service.list_products(empresaCodigo, days)
        return {"success": True, "data": data, "namespace": "executive"}
    except Exception as e:
        logger.exception("elasticity-products: %s", e)
        return {
            "success": True,
            "data": {"produtos": [], "success": False, "mensagem": str(e)},
            "fallback": True,
            "namespace": "executive",
        }


@router.get("/sales/elasticity-simulate", response_model=dict)
async def get_elasticity_simulate(
    empresaCodigo: int = Query(...),
    codigoProduto: str = Query(...),
    deltaPrecoRs: float = Query(0.0, ge=-0.5, le=0.5),
    days: int = Query(90, ge=7, le=180),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
):
    """Projeção: Δ%Volume = ε × Δ%Preço."""
    try:
        data = await _elasticity_service.simulate(
            empresaCodigo, codigoProduto, deltaPrecoRs, days
        )
        return {"success": True, "data": data, "namespace": "executive"}
    except Exception as e:
        logger.exception("elasticity-simulate: %s", e)
        return {
            "success": True,
            "data": {"success": False, "mensagem": str(e), "projecao": None},
            "fallback": True,
            "namespace": "executive",
        }


@router.get("/logistics/efficiency", response_model=dict)
async def get_logistics_efficiency(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: Optional[int] = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
):
    """
    Retorna eficiência logística, custos de frete e custo de oportunidade.
    """
    try:
        data = await _logistics_service.analyze(dataInicial, dataFinal, empresaCodigo)
        payload = data.model_dump() if hasattr(data, "model_dump") else data
        return {"success": True, "data": payload, "namespace": "executive"}
    except Exception as e:
        logger.exception("Erro em logistics efficiency: %s", e)
        return {"success": False, "error": str(e)}

@router.get("/treasury/consolidation", response_model=dict)
async def get_treasury_consolidation(
    empresaCodigo: Optional[int] = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
):
    """
    Retorna consolidação de saldos, aging de caixa e sugestões de sweep.
    """
    try:
        data = await _treasury_service.analyze(empresaCodigo)
        return {"success": True, "data": data, "namespace": "executive"}
    except Exception as e:
        logger.error(f"Erro em treasury consolidation: {str(e)}")
        return {"success": False, "error": str(e)}
