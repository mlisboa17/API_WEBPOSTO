"""Rota de Previsao de Estoque e Sugestao de Compras.

Sprint 58/59-B: Endpoint dinamico por empresa/fornecedor.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.services.inventory_prediction_service import (
    InventoryPredictionService,
    TankPrediction,
)
from src.services.company_settings_service import get_company_settings_service
from src.services.webposto_integration_service import get_webposto_integration_service
from src.services.external_market_service import get_external_market_service

router = APIRouter(prefix="/api/v1/operational", tags=["Operational"])


class TankPredictionDTO(BaseModel):
    """DTO de predicao para um tanque."""
    
    produto_codigo: int
    produto_nome: str
    tipo_combustivel: str
    
    estoque_atual_litros: float
    capacidade_tanque: float
    ocupacao_percentual: float
    
    consumo_medio_diario: float
    dias_cobertura_desejado: int
    lead_time_horas: int
    
    autonomia_horas_restantes: float
    autonomia_dias_restantes: float
    
    status_alerta: str
    sugestao_compra_litros: float
    alerta_label: str = "Saudável"
    
    dias_historico_usado: int
    observacoes: list[str] = Field(default_factory=list)
    cpm_rs_litro: float = 0.0
    preco_venda_rs_litro: float = 0.0
    margem_bruta_rs_litro: float = 0.0
    valor_estoque_imobilizado_rs: float = 0.0
    cpm_origem: str = ""
    data_hora_medidor: str | None = None
    
    @classmethod
    def from_prediction(cls, p: TankPrediction) -> "TankPredictionDTO":
        return cls(
            produto_codigo=p.produto_codigo,
            produto_nome=p.produto_nome,
            tipo_combustivel=p.tipo_combustivel,
            estoque_atual_litros=p.estoque_atual_litros,
            capacidade_tanque=p.capacidade_tanque,
            ocupacao_percentual=p.ocupacao_percentual,
            consumo_medio_diario=p.consumo_medio_diario,
            dias_cobertura_desejado=p.dias_cobertura_desejado,
            lead_time_horas=p.lead_time_horas,
            autonomia_horas_restantes=p.autonomia_horas_restantes,
            autonomia_dias_restantes=p.autonomia_dias_restantes,
            status_alerta=p.status_alerta,
            sugestao_compra_litros=p.sugestao_compra_litros,
            alerta_label=getattr(p, "alerta_label", "Saudável"),
            dias_historico_usado=p.dias_historico_usado,
            observacoes=p.observacoes,
            cpm_rs_litro=getattr(p, "cpm_rs_litro", 0.0),
            preco_venda_rs_litro=getattr(p, "preco_venda_rs_litro", 0.0),
            margem_bruta_rs_litro=getattr(p, "margem_bruta_rs_litro", 0.0),
            valor_estoque_imobilizado_rs=getattr(p, "valor_estoque_imobilizado_rs", 0.0),
            cpm_origem=getattr(p, "cpm_origem", ""),
            data_hora_medidor=getattr(p, "data_hora_medidor", None),
        )


class InventoryPredictionResponse(BaseModel):
    """Resposta do endpoint de previsao de estoque."""
    
    success: bool = True
    empresa_codigo: int
    empresa_nome: str
    data_calculo: str
    
    dias_cobertura: int
    lead_time_horas: int
    
    predicoes: list[TankPredictionDTO] = Field(default_factory=list)
    
    total_sugestao_compra_litros: float = 0.0
    tanques_com_alerta: int = 0
    tanques_urgentes: int = 0
    
    observacoes: list[str] = Field(default_factory=list)


@router.get("/inventory-prediction", response_model=InventoryPredictionResponse)
async def get_inventory_prediction(
    empresaCodigo: int = Query(
        ...,
        description="Codigo da filial (5555=Casa Caiada, 6666=VIP, 74014=Real)"
    ),
    dias_cobertura: int | None = Query(
        None,
        ge=1,
        le=15,
        description="Dias de estoque desejado (usa config da empresa se nao informado)"
    ),
    lead_time_horas: int | None = Query(
        None,
        ge=1,
        le=168,
        description="Tempo de entrega (usa config do fornecedor se nao informado)"
    ),
    fornecedor_codigo: str | None = Query(
        None,
        description="Codigo do fornecedor (usa principal da empresa se nao informado)"
    ),
) -> InventoryPredictionResponse:
    """
    Calcula previsao de run-out e sugestao de compras para cada tanque.
    
    - Analisa estoque atual vs consumo medio diario
    - Projeta autonomia em horas/dias ate esgotamento
    - Sugere volume de compra para atingir meta de cobertura
    - Classifica alertas: OK, ATENCAO, COMPRA_URGENTE
    - Usa configuracoes dinamicas da empresa/fornecedor
    """
    
    service = InventoryPredictionService()
    result = await service.predict(
        empresa_codigo=empresaCodigo,
        dias_cobertura=dias_cobertura,
        lead_time_horas=lead_time_horas,
        fornecedor_codigo=fornecedor_codigo,
    )
    
    return InventoryPredictionResponse(
        success=result.success,
        empresa_codigo=result.empresa_codigo,
        empresa_nome=result.empresa_nome,
        data_calculo=result.data_calculo,
        dias_cobertura=result.dias_cobertura,
        lead_time_horas=result.lead_time_horas,
        predicoes=[TankPredictionDTO.from_prediction(p) for p in result.predicoes],
        total_sugestao_compra_litros=result.total_sugestao_compra_litros,
        tanques_com_alerta=result.tanques_com_alerta,
        tanques_urgentes=result.tanques_urgentes,
        observacoes=result.observacoes,
    )


@router.get("/inventory-prediction/settings")
async def get_prediction_settings(
    empresaCodigo: int = Query(..., description="Codigo da filial"),
) -> dict[str, Any]:
    """Retorna configuracoes de previsao para a empresa."""
    
    settings_svc = get_company_settings_service()
    settings = settings_svc.get_settings(empresaCodigo)
    fornecedor = settings_svc.get_supplier(empresaCodigo)
    geo = get_external_market_service().get_branch_coordinates(empresaCodigo)
    
    return {
        "empresa_codigo": settings.empresa_codigo,
        "empresa_nome": settings.empresa_nome,
        "dias_cobertura_padrao": settings.dias_cobertura_padrao,
        "lead_time_padrao_horas": settings.lead_time_padrao_horas,
        "regiao": settings.regiao,
        "terminal_padrao": settings.terminal_padrao,
        "latitude": settings.latitude,
        "longitude": settings.longitude,
        "geo": geo[0] if geo else None,
        "fornecedor_principal": {
            "codigo": fornecedor.codigo if fornecedor else None,
            "nome": fornecedor.nome if fornecedor else None,
            "lead_time_horas": fornecedor.lead_time_horas if fornecedor else None,
        } if fornecedor else None,
        "fornecedores_disponiveis": [
            {"codigo": f.codigo, "nome": f.nome, "lead_time_horas": f.lead_time_horas}
            for f in settings.fornecedores if f.ativo
        ],
    }


@router.get("/realtime-bundle")
async def get_realtime_operational_bundle(
    empresaCodigo: int = Query(..., description="Codigo da filial"),
) -> dict[str, Any]:
    """
    Pacote operacional real: vendas do dia + tanques + CPM via webPosto.
    Usado pelo modulo de inteligencia preditiva e compras.
    """
    integration = get_webposto_integration_service()
    try:
        return {"success": True, "data": await integration.get_operational_bundle(empresaCodigo)}
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "data": {
                "empresa_codigo": empresaCodigo,
                "vendas_dia": {"sucesso": False, "mensagem": str(exc)},
                "tanques": {"sucesso": False, "mensagem": str(exc)},
                "cpm": {"sucesso": False, "mensagem": str(exc)},
            },
        }


@router.get("/tank-discharge-history")
async def get_tank_discharge_history(
    empresaCodigo: int = Query(..., description="Codigo da filial"),
    fuel: str | None = Query(None, description="Nome/tipo do combustivel"),
    produtoCodigo: int | None = Query(None),
    tanqueId: int | None = Query(None),
    dias: int = Query(45, ge=7, le=90),
    limit: int = Query(20, ge=1, le=50),
) -> dict[str, Any]:
    """Histórico real de descarga (COMPRA/COMPRA_ITEM ou LMC_REDE)."""
    from src.services.tank_discharge_history_service import (
        get_tank_discharge_history_service,
    )

    try:
        return await get_tank_discharge_history_service().get_history(
            empresa_codigo=empresaCodigo,
            fuel=fuel,
            produto_codigo=produtoCodigo,
            tanque_id=tanqueId,
            dias=dias,
            limit=limit,
        )
    except Exception as exc:
        return {
            "success": False,
            "empresa_codigo": empresaCodigo,
            "fonte": "error",
            "items": [],
            "observacoes": [str(exc)],
        }
