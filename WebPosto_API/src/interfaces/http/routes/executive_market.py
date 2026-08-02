"""Sprint 55 — Rotas de Market Competitiveness: benchmark, spread e competidores.

Motor 100% dinâmico - parâmetros lidos de CompanySettings.
"""
from __future__ import annotations
import logging
from typing import Optional, Any
from fastapi import APIRouter, Depends, Query

from src.interfaces.http.authz import require_roles
from src.services.market_competitiveness_service import MarketCompetitivenessService
from src.services.company_settings_service import get_company_settings_service
from src.interfaces.http.schemas.executive_market_schema import (
    CompetitorPriceCreate,
    CompetitorPrice,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive/market",
    tags=["Executive Market S55"],
)

_service = MarketCompetitivenessService()


@router.get("/benchmark", response_model=dict)
async def get_market_benchmark(
    empresaCodigo: Optional[int] = Query(None, description="Codigo da empresa/filial (usa config padrao se None)"),
    margemMinimaPct: Optional[float] = Query(None, ge=0.0, le=50.0, description="Margem minima % (usa config da empresa se None)"),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
):
    """
    Retorna benchmark de preços: Lisboa vs concorrentes da região, spread e alertas de squeeze.
    
    100% dinâmico - preços e limites lidos das configurações da empresa.
    """
    try:
        data = _service.get_benchmark(empresaCodigo, margemMinimaPct)
        return {"success": True, "data": data, "namespace": "executive"}
    except Exception as e:
        logger.error(f"Erro em market benchmark: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/competitor-prices", response_model=dict)
async def list_competitor_prices(
    empresaCodigo: Optional[int] = Query(None, description="Codigo da empresa/filial"),
    produtoCodigo: Optional[str] = Query(None, description="Codigo do produto (GC, GA, EH, DS10, etc)"),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
):
    """
    Lista preços registrados dos concorrentes para a empresa/produto.
    """
    try:
        data = _service.list_competitor_prices(empresaCodigo, produtoCodigo, limit)
        return {"success": True, "data": data, "namespace": "executive"}
    except Exception as e:
        logger.error(f"Erro em competitor prices: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/competitor-prices", response_model=dict)
async def register_competitor_price(
    payload: CompetitorPriceCreate,
    empresaCodigo: Optional[int] = Query(None, description="Codigo da empresa/filial"),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
):
    """
    Registra preço praticado por um concorrente da região.
    """
    try:
        data = _service.register_competitor_price(payload.model_dump(), empresaCodigo)
        return {"success": True, "data": data, "namespace": "executive"}
    except Exception as e:
        logger.error(f"Erro ao registrar competitor price: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/settings/products")
async def list_fuel_products(
    empresaCodigo: Optional[int] = Query(None, description="Codigo da empresa (None para produtos globais)"),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict[str, Any]:
    """Lista produtos de combustível configurados (dinâmico por empresa)."""
    settings_svc = get_company_settings_service()
    return {
        "success": True,
        "data": settings_svc.list_fuel_products(empresaCodigo),
        "namespace": "executive",
    }


@router.get("/settings/suppliers")
async def list_suppliers(
    empresaCodigo: Optional[int] = Query(None, description="Codigo da empresa (None para fornecedores globais)"),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict[str, Any]:
    """Lista fornecedores configurados (dinâmico por empresa)."""
    settings_svc = get_company_settings_service()
    return {
        "success": True,
        "data": settings_svc.list_suppliers(empresaCodigo),
        "namespace": "executive",
    }


@router.get("/settings/companies")
async def list_companies(
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict[str, Any]:
    """Lista todas as empresas/filiais configuradas."""
    settings_svc = get_company_settings_service()
    return {
        "success": True,
        "data": settings_svc.list_companies(),
        "namespace": "executive",
    }


@router.get("/settings/pricing")
async def get_pricing(
    empresaCodigo: int = Query(..., description="Codigo da empresa/filial"),
    produtoCodigo: Optional[str] = Query(None, description="Codigo do produto (None para todos)"),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict[str, Any]:
    """Retorna preços e custos configurados para a empresa."""
    settings_svc = get_company_settings_service()
    
    if produtoCodigo:
        pricing = settings_svc.get_product_pricing(empresaCodigo, produtoCodigo)
        data = pricing.__dict__ if pricing else None
    else:
        all_pricing = settings_svc.get_all_products_pricing(empresaCodigo)
        data = {code: p.__dict__ for code, p in all_pricing.items()}
    
    return {
        "success": True,
        "data": data,
        "namespace": "executive",
    }


@router.put("/settings/pricing")
async def update_pricing(
    empresaCodigo: int = Query(..., description="Codigo da empresa/filial"),
    produtoCodigo: str = Query(..., description="Codigo do produto"),
    precoVenda: Optional[float] = Query(None, ge=0.0, description="Preco de venda R$"),
    custoAquisicao: Optional[float] = Query(None, ge=0.0, description="Custo de aquisicao R$"),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict[str, Any]:
    """Atualiza preço/custo de um produto para a empresa."""
    settings_svc = get_company_settings_service()
    
    updated = settings_svc.update_product_pricing(
        empresaCodigo, produtoCodigo, precoVenda, custoAquisicao
    )
    
    if not updated:
        return {"success": False, "error": "Produto nao encontrado"}
    
    _service.clear_cache(empresaCodigo)
    
    return {
        "success": True,
        "data": updated.__dict__,
        "namespace": "executive",
    }
