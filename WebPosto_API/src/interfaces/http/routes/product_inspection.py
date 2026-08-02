"""Rota de inspeção de produtos e grupos de combustíveis — Sprint 57-G.

Mapeia a estrutura real de cadastro de produtos do WebPosto para identificar
grupos e categorias de combustíveis (Gasolinas, Etanóis, Diesels, GNV).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query

from src.gateway.shared_client import get_webposto_client
from src.services.produto_catalog import ProdutoCatalogService

router = APIRouter(prefix="/api/v1/inspection", tags=["Inspeção"])
logger = logging.getLogger(__name__)


def _classify_fuel_type(name: str, group_name: str, tipo_combustivel: str) -> str | None:
    """Classifica o tipo de combustível baseado no nome e grupo."""
    name_upper = (name or "").upper()
    group_upper = (group_name or "").upper()
    tipo_upper = (tipo_combustivel or "").upper()
    
    if any(kw in name_upper or kw in group_upper or kw in tipo_upper for kw in ["GNV", "GAS NATURAL"]):
        return "GNV"
    if any(kw in name_upper or kw in group_upper for kw in ["DIESEL", "S10", "S500", "S-10", "S-500"]):
        return "DIESEL"
    if any(kw in name_upper or kw in group_upper for kw in ["ETANOL", "ALCOOL", "ÁLCOOL", "EAC", "EHC"]):
        return "ETANOL"
    if any(kw in name_upper or kw in group_upper for kw in ["GASOLINA", "GAS COMUM", "ADITIVADA", "PREMIUM"]):
        return "GASOLINA"
    return None


@router.get("/fuel-products")
async def inspect_fuel_products(
    empresaCodigo: int | None = Query(None, description="Código da empresa (opcional)"),
) -> dict[str, Any]:
    """
    Inspeciona e mapeia todos os produtos de combustíveis do cadastro WebPosto.
    
    Retorna:
    - Lista completa de grupos de combustíveis
    - Produtos classificados por tipo (Gasolina, Etanol, Diesel, GNV)
    - Campos identificadores (grupoCodigo, tipoProduto, tipoCombustivel)
    """
    client = get_webposto_client()
    catalog_service = ProdutoCatalogService(client)
    
    company_codes = [empresaCodigo] if empresaCodigo else [11495, 5555, 74014]
    
    catalog_resp = await catalog_service.get_catalog(company_codes)
    
    if not catalog_resp.success:
        return {
            "success": False,
            "error": str(catalog_resp.error),
            "fuel_groups": [],
            "fuel_products": [],
        }
    
    products = catalog_resp.data.get("products", [])
    
    fuel_groups: dict[int, dict[str, Any]] = {}
    fuel_products: list[dict[str, Any]] = []
    non_fuel_groups: dict[int, str] = {}
    
    for prod in products:
        is_fuel = prod.get("combustivel", False)
        group_code = prod.get("grupoCodigo")
        group_name = prod.get("grupoProduto", "")
        tipo_combustivel = prod.get("tipoCombustivel", "")
        name = prod.get("nomeProduto", "")
        
        fuel_type = _classify_fuel_type(name, group_name, tipo_combustivel)
        
        if is_fuel or fuel_type:
            if group_code is not None:
                fuel_groups[group_code] = {
                    "grupoCodigo": group_code,
                    "grupoProduto": group_name,
                    "tipoCombustivel": tipo_combustivel,
                    "tipoClassificado": fuel_type or "COMBUSTIVEL_OUTROS",
                }
            
            fuel_products.append({
                "produtoCodigo": prod.get("produtoCodigo"),
                "nomeProduto": name,
                "grupoCodigo": group_code,
                "grupoProduto": group_name,
                "tipoProduto": prod.get("tipoProduto"),
                "tipoCombustivel": tipo_combustivel,
                "combustivel": is_fuel,
                "tipoClassificado": fuel_type or "COMBUSTIVEL_OUTROS",
                "ativo": prod.get("ativo"),
                "produtoLmcCodigo": prod.get("produtoLmcCodigo"),
            })
        else:
            if group_code is not None:
                non_fuel_groups[group_code] = group_name
    
    fuel_groups_list = sorted(fuel_groups.values(), key=lambda x: x.get("grupoCodigo") or 0)
    
    by_type: dict[str, list[dict]] = {
        "GASOLINA": [],
        "ETANOL": [],
        "DIESEL": [],
        "GNV": [],
        "COMBUSTIVEL_OUTROS": [],
    }
    
    for fp in fuel_products:
        tipo = fp.get("tipoClassificado", "COMBUSTIVEL_OUTROS")
        by_type.setdefault(tipo, []).append(fp)
    
    fuel_group_codes = list(fuel_groups.keys())
    
    return {
        "success": True,
        "summary": {
            "total_products_inspected": len(products),
            "total_fuel_products": len(fuel_products),
            "total_fuel_groups": len(fuel_groups),
            "fuel_group_codes": fuel_group_codes,
            "breakdown": {
                "GASOLINA": len(by_type.get("GASOLINA", [])),
                "ETANOL": len(by_type.get("ETANOL", [])),
                "DIESEL": len(by_type.get("DIESEL", [])),
                "GNV": len(by_type.get("GNV", [])),
                "OUTROS": len(by_type.get("COMBUSTIVEL_OUTROS", [])),
            },
        },
        "fuel_groups": fuel_groups_list,
        "fuel_products_by_type": {
            "GASOLINA": by_type.get("GASOLINA", []),
            "ETANOL": by_type.get("ETANOL", []),
            "DIESEL": by_type.get("DIESEL", []),
            "GNV": by_type.get("GNV", []),
            "OUTROS": by_type.get("COMBUSTIVEL_OUTROS", []),
        },
        "non_fuel_group_codes": list(non_fuel_groups.keys()),
        "identification_fields": {
            "primary": "grupoCodigo",
            "secondary": "tipoCombustivel",
            "tertiary": "combustivel (boolean)",
            "name_patterns": ["GASOLINA", "ETANOL", "DIESEL", "GNV", "S10", "S500", "ADITIVADA"],
        },
    }


@router.get("/abastecimento-sample")
async def inspect_abastecimento_sample(
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: int | None = Query(None, description="Código da empresa"),
    limit: int = Query(10, description="Limite de registros para amostra"),
) -> dict[str, Any]:
    """
    Inspeciona uma amostra de abastecimentos para verificar estrutura de dados.
    """
    from src.services.abastecimento_service import AbastecimentoService
    
    client = get_webposto_client()
    abast_service = AbastecimentoService(client)
    
    resp = await abast_service.get_periodo(dataInicial, dataFinal)
    
    if not resp.success:
        return {
            "success": False,
            "error": str(resp.error),
            "sample": [],
        }
    
    raw = resp.data
    if isinstance(raw, dict):
        records = raw.get("dados") or raw.get("data") or raw.get("resultados") or []
    elif isinstance(raw, list):
        records = raw
    else:
        records = []
    
    if empresaCodigo:
        records = [r for r in records if int(r.get("empresaCodigo") or 0) == empresaCodigo]
    
    unique_products: dict[int, dict] = {}
    total_litros = 0.0
    total_valor = 0.0
    
    for r in records:
        prod_code = r.get("produtoCodigo")
        prod_name = r.get("nomeProduto") or r.get("produtoNome") or r.get("descricaoProduto") or ""
        litros = float(r.get("quantidadeLitros") or r.get("litros") or 0)
        valor = float(r.get("valorVenda") or r.get("valor") or 0)
        
        total_litros += litros
        total_valor += valor
        
        if prod_code and prod_code not in unique_products:
            unique_products[prod_code] = {
                "produtoCodigo": prod_code,
                "nomeProduto": prod_name,
                "grupoCodigo": r.get("grupoCodigo"),
            }
    
    return {
        "success": True,
        "period": {"start": dataInicial, "end": dataFinal},
        "empresa_filter": empresaCodigo,
        "totals": {
            "registros": len(records),
            "litros": round(total_litros, 2),
            "valor_rs": round(total_valor, 2),
        },
        "unique_products": list(unique_products.values()),
        "sample": records[:limit],
        "fields_available": list(records[0].keys()) if records else [],
    }
