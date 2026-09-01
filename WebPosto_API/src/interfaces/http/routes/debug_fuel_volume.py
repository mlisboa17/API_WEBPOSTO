"""Endpoint de Debug - Auditoria Isolada de Volumetria Fisica.

Sprint 57-H: Diagnostico de volume real por posto/dia diretamente da API WebPosto.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.gateway.shared_client import get_webposto_client

router = APIRouter(prefix="/api/v1/debug", tags=["Debug"])

FUEL_KEYWORDS = {
    "GASOLINA": ["GASOLINA", "GAS COMUM", "ADITIVADA", "PREMIUM", "PODIUM", "GRID"],
    "ETANOL": ["ETANOL", "ALCOOL", "EAC", "EHC", "HIDRATADO"],
    "DIESEL": ["DIESEL", "S10", "S500", "S-10", "S-500"],
    "GNV": ["GNV", "GAS NATURAL"],
}


def classify_fuel(product_name: str) -> str | None:
    """Classifica o produto como tipo de combustivel."""
    name_upper = (product_name or "").upper()
    for fuel_type, keywords in FUEL_KEYWORDS.items():
        if any(kw in name_upper for kw in keywords):
            return fuel_type
    return None


class ProductVolume(BaseModel):
    produto_codigo: int
    produto_nome: str
    tipo_combustivel: str | None
    total_litros: float
    total_valor: float
    quantidade_abastecimentos: int


class FuelVolumeCheckResponse(BaseModel):
    success: bool = True
    posto: str = ""
    empresa_codigo: int = 0
    data_consulta: str = ""
    
    api_request: dict = Field(default_factory=dict)
    
    total_registros_api: int = 0
    total_registros_combustivel: int = 0
    
    volume_por_produto: list[ProductVolume] = Field(default_factory=list)
    
    resumo_por_tipo: dict[str, float] = Field(default_factory=dict)
    
    volume_total_litros: float = 0.0
    valor_total_rs: float = 0.0
    
    observacoes: list[str] = Field(default_factory=list)
    
    sample_record: dict = Field(default_factory=dict, description="Amostra do primeiro registro para debug")
    
    paginas_consultadas: int = 0


@router.get("/fuel-volume-check", response_model=FuelVolumeCheckResponse)
async def debug_fuel_volume_check(
    empresaCodigo: int = Query(5555, description="Codigo da empresa (5555=Casa Caiada, 6666=VIP, 74014=Real)"),
    data: str = Query(None, description="Data no formato YYYY-MM-DD (default: hoje)"),
) -> FuelVolumeCheckResponse:
    """
    AUDITORIA ISOLADA DE VOLUMETRIA FISICA
    
    Consulta diretamente a API /INTEGRACAO/ABASTECIMENTO do WebPosto
    e retorna o volume total de combustiveis (em litros) para um posto/dia.
    """
    
    if not data:
        data = str(date.today().isoformat())
    
    empresa_nomes = {
        5555: "AP Casa Caiada",
        6666: "Posto VIP", 
        74014: "Posto Real / Doze",
        11495: "Matriz",
    }
    
    response = FuelVolumeCheckResponse(
        posto=empresa_nomes.get(empresaCodigo, f"Empresa {empresaCodigo}"),
        empresa_codigo=empresaCodigo,
        data_consulta=data,
    )
    
    try:
        client = get_webposto_client()
        
        base_params = {
            "dataInicial": data,
            "dataFinal": data,
            "empresaCodigo": empresaCodigo,
        }
        
        response.api_request = {
            "endpoint": "/INTEGRACAO/ABASTECIMENTO",
            "params": base_params,
            "method": "GET",
            "paginacao": "ultimoCodigo (cursor)",
        }
        
        all_records: list[dict] = []
        ultimo_codigo: Any = None
        page = 0
        MAX_PAGES = 50
        
        while page < MAX_PAGES:
            page += 1
            params = {**base_params}
            if ultimo_codigo:
                params["ultimoCodigo"] = ultimo_codigo
            
            resp = await client.call_endpoint("abastecimento", params=params)
            
            if not resp.success:
                response.observacoes.append(f"Erro na pagina {page}: {resp.error}")
                break
            
            raw = resp.data
            batch: list[dict] = []
            new_ultimo: Any = None
            
            if isinstance(raw, dict):
                batch = raw.get("dados") or raw.get("data") or raw.get("resultados") or []
                new_ultimo = raw.get("ultimoCodigo")
            elif isinstance(raw, list):
                batch = raw
            
            if not batch:
                break
            
            all_records.extend(batch)
            
            if new_ultimo is None or new_ultimo == ultimo_codigo:
                break
            
            ultimo_codigo = new_ultimo
            
            if len(batch) < 200:
                break
        
        records = all_records
        response.paginas_consultadas = page
        response.observacoes.append(f"Paginacao: {page} pagina(s) consultadas, {len(records)} registros totais")
        
        response.total_registros_api = len(records)
        
        volume_por_produto: dict[int, dict[str, Any]] = defaultdict(lambda: {
            "produto_nome": "",
            "tipo_combustivel": None,
            "total_litros": 0.0,
            "total_valor": 0.0,
            "quantidade": 0,
        })
        
        registros_combustivel = 0
        volume_total = 0.0
        valor_total = 0.0
        
        if records:
            response.sample_record = dict(records[0])
        
        for record in records:
            prod_codigo = (
                record.get("produtoCodigo") 
                or record.get("produtoLmcCodigo")
                or record.get("codigoProduto")
                or record.get("produto_codigo") 
                or 0
            )
            try:
                prod_codigo = int(prod_codigo)
            except:
                prod_codigo = 0
                
            prod_nome = str(
                record.get("produtoDescricao") 
                or record.get("descricaoProduto")
                or record.get("nomeProduto") 
                or record.get("produtoNome")
                or record.get("combustivel")
                or record.get("tipoCombustivel")
                or record.get("produto")
                or ""
            ).strip()
            
            litros = float(
                record.get("quantidadeLitros") 
                or record.get("litros") 
                or record.get("quantidade") 
                or record.get("volume")
                or 0
            )
            valor = float(
                record.get("valorVenda") 
                or record.get("valor") 
                or record.get("valorTotal")
                or record.get("valorUnitario", 0) * litros
                or 0
            )
            
            tipo_combustivel = classify_fuel(prod_nome)
            
            if tipo_combustivel or litros > 0:
                registros_combustivel += 1
                volume_total += litros
                valor_total += valor
                
                entry = volume_por_produto[prod_codigo]
                entry["produto_nome"] = prod_nome or entry["produto_nome"] or f"Produto {prod_codigo}"
                entry["tipo_combustivel"] = tipo_combustivel
                entry["total_litros"] += litros
                entry["total_valor"] += valor
                entry["quantidade"] += 1
        
        response.total_registros_combustivel = registros_combustivel
        response.volume_total_litros = round(volume_total, 2)
        response.valor_total_rs = round(valor_total, 2)
        
        produtos_list = []
        for prod_codigo, dados in sorted(volume_por_produto.items(), key=lambda x: x[1]["total_litros"], reverse=True):
            pv = ProductVolume(
                produto_codigo=prod_codigo,
                produto_nome=dados["produto_nome"],
                tipo_combustivel=dados["tipo_combustivel"],
                total_litros=round(dados["total_litros"], 2),
                total_valor=round(dados["total_valor"], 2),
                quantidade_abastecimentos=dados["quantidade"],
            )
            produtos_list.append(pv)
        
        response.volume_por_produto = produtos_list
        
        resumo_tipo: dict[str, float] = defaultdict(float)
        for pv in produtos_list:
            tipo = pv.tipo_combustivel or "OUTROS"
            resumo_tipo[tipo] += pv.total_litros
        
        response.resumo_por_tipo = {k: round(v, 2) for k, v in resumo_tipo.items()}
        
        if volume_total == 0:
            response.observacoes.append("[AVISO] Nenhum volume encontrado - verificar se ha movimento no dia")
        
        return response
        
    except Exception as e:
        response.success = False
        response.observacoes.append(f"Excecao: {str(e)}")
        return response
