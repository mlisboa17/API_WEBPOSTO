"""Rotas do Motor de Alertas Proativos.

Sprint 59-B: API dinamica para gestao de alertas e inteligencia de mercado.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.services.alert_engine_service import (
    AlertCategory,
    AlertEngineService,
    AlertSeverity,
    AlertStatus,
    ProactiveAlert,
    get_alert_engine,
    SEVERITY_THRESHOLDS,
    RENOTIFICATION_INTERVALS,
)
from src.services.fuel_market_intelligence_service import (
    FuelPriceAnalysis,
    get_market_intelligence,
)
from src.services.company_settings_service import (
    get_company_settings_service,
)

router = APIRouter(prefix="/api/v1/executive/alerts", tags=["Alerts"])


class AlertDTO(BaseModel):
    """DTO de alerta proativo."""
    
    id: str
    category: str
    severity: str
    status: str
    
    title: str
    description: str
    justificativa: str
    
    impact_rs: float
    empresa_codigo: int
    empresa_nome: str
    
    operador: str | None = None
    bico: int | None = None
    turno: str | None = None
    produto: str | None = None
    
    created_at: str
    updated_at: str
    expires_at: str | None = None
    
    notification_count: int = 0
    last_notification_at: str | None = None
    renotification_interval_min: int = 30
    
    renotification_active: bool = False
    
    @classmethod
    def from_alert(cls, alert: ProactiveAlert) -> "AlertDTO":
        return cls(
            id=alert.id,
            category=alert.category.value,
            severity=alert.severity.value,
            status=alert.status.value,
            title=alert.title,
            description=alert.description,
            justificativa=alert.justificativa,
            impact_rs=alert.impact_rs,
            empresa_codigo=alert.empresa_codigo,
            empresa_nome=alert.empresa_nome,
            operador=alert.operador,
            bico=alert.bico,
            turno=alert.turno,
            produto=alert.produto,
            created_at=alert.created_at.isoformat(),
            updated_at=alert.updated_at.isoformat(),
            expires_at=alert.expires_at.isoformat() if alert.expires_at else None,
            notification_count=alert.notification_count,
            last_notification_at=alert.last_notification_at.isoformat() if alert.last_notification_at else None,
            renotification_interval_min=alert.renotification_interval_min,
            renotification_active=(
                alert.severity == AlertSeverity.CRITICO and
                alert.status in [AlertStatus.PENDENTE, AlertStatus.VISUALIZADO]
            ),
        )


class AlertSummaryResponse(BaseModel):
    """Resumo dos alertas."""
    
    total_pendentes: int
    criticos: int
    medios: int
    baixos: int
    impacto_total_rs: float
    aguardando_renotificacao: int
    
    thresholds: dict[str, float] = Field(default_factory=dict)
    renotification_intervals: dict[str, str] = Field(default_factory=dict)


class CreateAlertRequest(BaseModel):
    """Request para criar alerta."""
    
    category: str
    title: str
    description: str
    impact_rs: float
    empresa_codigo: int
    empresa_nome: str = ""
    justificativa: str = ""
    operador: str | None = None
    bico: int | None = None
    turno: str | None = None
    produto: str | None = None


class UpdateAlertStatusRequest(BaseModel):
    """Request para atualizar status."""
    
    status: str
    resolved_by: str | None = None
    resolution_note: str | None = None


class MarketAnalysisResponse(BaseModel):
    """Resposta de analise de mercado dinamica."""
    
    empresa_codigo: int
    empresa_nome: str
    
    produto_codigo: str
    produto_nome: str
    categoria: str
    
    preco_base: float
    preco_ajustado: float
    
    fator_sazonalidade: float
    fator_mercado: float
    fator_total: float
    
    fornecedor_nome: str
    terminal: str
    regiao: str
    
    periodo_safra: bool
    descricao_periodo: str
    
    justificativa: str
    recomendacao: str
    
    data_analise: str


@router.get("/engine/summary", response_model=AlertSummaryResponse)
async def get_alerts_summary() -> AlertSummaryResponse:
    """Retorna resumo dos alertas com matriz de criticidade."""
    
    engine = get_alert_engine()
    summary = engine.get_summary()
    
    return AlertSummaryResponse(
        **summary,
        thresholds={k.value: v for k, v in SEVERITY_THRESHOLDS.items()},
        renotification_intervals={str(k): v for k, v in RENOTIFICATION_INTERVALS.items()},
    )


@router.get("/engine/list", response_model=list[AlertDTO])
async def list_alerts(
    severity: str | None = Query(None, description="Filtrar por severidade: CRITICO, MEDIO, BAIXO"),
    status: str | None = Query(None, description="Filtrar por status: PENDENTE, VISUALIZADO, APROVADO, REJEITADO, EXPIRADO"),
    empresa_codigo: int | None = Query(None, description="Filtrar por empresa"),
) -> list[AlertDTO]:
    """Lista alertas com filtros opcionais."""
    
    engine = get_alert_engine()
    
    sev = AlertSeverity(severity) if severity else None
    stat = AlertStatus(status) if status else None
    
    alerts = engine.get_alerts_by_severity(
        severity=sev,
        empresa_codigo=empresa_codigo,
        status=stat,
    )
    
    return [AlertDTO.from_alert(a) for a in alerts]


@router.get("/engine/pending-renotifications", response_model=list[AlertDTO])
async def get_pending_renotifications() -> list[AlertDTO]:
    """Retorna alertas criticos aguardando re-notificacao."""
    
    engine = get_alert_engine()
    pending = engine.get_pending_renotifications()
    
    return [AlertDTO.from_alert(a) for a in pending]


@router.post("/engine/create", response_model=AlertDTO)
async def create_alert(request: CreateAlertRequest) -> AlertDTO:
    """Cria um novo alerta proativo."""
    
    engine = get_alert_engine()
    
    try:
        category = AlertCategory(request.category)
    except ValueError:
        category = AlertCategory.QUEBRA_CAIXA
    
    alert = engine.create_alert(
        category=category,
        title=request.title,
        description=request.description,
        impact_rs=request.impact_rs,
        empresa_codigo=request.empresa_codigo,
        empresa_nome=request.empresa_nome,
        justificativa=request.justificativa,
        operador=request.operador,
        bico=request.bico,
        turno=request.turno,
        produto=request.produto,
    )
    
    return AlertDTO.from_alert(alert)


@router.patch("/engine/{alert_id}/status", response_model=AlertDTO)
async def update_alert_status(
    alert_id: str,
    request: UpdateAlertStatusRequest,
) -> AlertDTO:
    """Atualiza status de um alerta."""
    
    engine = get_alert_engine()
    
    try:
        status = AlertStatus(request.status)
    except ValueError:
        status = AlertStatus.PENDENTE
    
    success = engine.update_status(
        alert_id=alert_id,
        status=status,
        resolved_by=request.resolved_by,
        resolution_note=request.resolution_note,
    )
    
    if not success or alert_id not in engine.alerts:
        return AlertDTO(
            id=alert_id,
            category="",
            severity="",
            status="NOT_FOUND",
            title="Alerta nao encontrado",
            description="",
            justificativa="",
            impact_rs=0,
            empresa_codigo=0,
            empresa_nome="",
            created_at="",
            updated_at="",
        )
    
    return AlertDTO.from_alert(engine.alerts[alert_id])


@router.post("/engine/{alert_id}/mark-notified")
async def mark_alert_notified(alert_id: str) -> dict[str, Any]:
    """Marca alerta como notificado (incrementa contador)."""
    
    engine = get_alert_engine()
    success = engine.mark_notified(alert_id)
    
    return {"success": success, "alert_id": alert_id}


@router.get("/market/analysis", response_model=MarketAnalysisResponse)
async def get_market_analysis(
    empresa_codigo: int = Query(5555, description="Codigo da empresa/filial"),
    produto_codigo: str = Query("EH", description="Codigo do produto (GC, GA, EH, DS10, etc)"),
    fornecedor_codigo: str | None = Query(None, description="Codigo do fornecedor (opcional, usa principal)"),
) -> MarketAnalysisResponse:
    """Retorna analise de mercado dinamica para empresa/produto/fornecedor."""
    
    market = get_market_intelligence()
    settings_svc = get_company_settings_service()

    try:
        await market.refresh_market_indicators()
    except Exception:
        pass
    
    analysis = market.analyze_price(
        empresa_codigo=empresa_codigo,
        produto_codigo=produto_codigo,
        fornecedor_codigo=fornecedor_codigo,
    )
    
    settings = settings_svc.get_settings(empresa_codigo)
    
    return MarketAnalysisResponse(
        empresa_codigo=empresa_codigo,
        empresa_nome=settings.empresa_nome,
        produto_codigo=analysis.produto_codigo,
        produto_nome=analysis.produto_nome,
        categoria=analysis.categoria,
        preco_base=analysis.preco_base,
        preco_ajustado=analysis.preco_ajustado,
        fator_sazonalidade=analysis.fator_sazonalidade,
        fator_mercado=analysis.fator_mercado,
        fator_total=analysis.fator_total,
        fornecedor_nome=analysis.fornecedor_nome,
        terminal=analysis.terminal,
        regiao=analysis.regiao,
        periodo_safra=analysis.periodo_safra,
        descricao_periodo=analysis.descricao_periodo,
        justificativa=analysis.justificativa,
        recomendacao=analysis.recomendacao,
        data_analise=analysis.data_analise.isoformat(),
    )


@router.get("/market/analysis/all")
async def get_all_products_analysis(
    empresa_codigo: int = Query(5555, description="Codigo da empresa/filial"),
    fornecedor_codigo: str | None = Query(None, description="Codigo do fornecedor"),
) -> list[MarketAnalysisResponse]:
    """Retorna analise de mercado para todos os produtos da empresa."""
    
    market = get_market_intelligence()
    settings_svc = get_company_settings_service()
    
    analyses = market.analyze_all_products(
        empresa_codigo=empresa_codigo,
        fornecedor_codigo=fornecedor_codigo,
    )
    
    settings = settings_svc.get_settings(empresa_codigo)
    
    return [
        MarketAnalysisResponse(
            empresa_codigo=empresa_codigo,
            empresa_nome=settings.empresa_nome,
            produto_codigo=a.produto_codigo,
            produto_nome=a.produto_nome,
            categoria=a.categoria,
            preco_base=a.preco_base,
            preco_ajustado=a.preco_ajustado,
            fator_sazonalidade=a.fator_sazonalidade,
            fator_mercado=a.fator_mercado,
            fator_total=a.fator_total,
            fornecedor_nome=a.fornecedor_nome,
            terminal=a.terminal,
            regiao=a.regiao,
            periodo_safra=a.periodo_safra,
            descricao_periodo=a.descricao_periodo,
            justificativa=a.justificativa,
            recomendacao=a.recomendacao,
            data_analise=a.data_analise.isoformat(),
        )
        for a in analyses
    ]


@router.get("/market/alerts")
async def get_market_alerts(
    empresa_codigo: int = Query(5555, description="Codigo da empresa/filial"),
) -> list[dict[str, Any]]:
    """Retorna alertas de mercado para a empresa."""
    
    market = get_market_intelligence()
    return market.generate_market_alerts(empresa_codigo)


@router.get("/market/indicators")
async def get_market_indicators(
    force_refresh: bool = Query(False, description="Forca nova consulta as APIs externas"),
) -> dict[str, Any]:
    """Retorna indicadores de mercado atuais (USD, Brent, Esalq) de fontes reais."""
    
    market = get_market_intelligence()
    try:
        return await market.refresh_market_indicators(force=force_refresh)
    except Exception as exc:
        # Nunca derruba o painel: devolve cache/fallback
        payload = market.get_market_indicators()
        payload["warnings"] = [f"Falha ao atualizar indicadores externos: {exc}"]
        payload["fonte"] = "fallback_cache"
        return payload


@router.put("/market/indicators/esalq-override")
async def put_esalq_override(
    empresaCodigo: int = Query(5555, description="Filial dona do override"),
    esalqPe: float | None = Query(None, description="Cotação Esalq PE (R$/L)"),
    esalqAl: float | None = Query(None, description="Cotação Esalq AL (R$/L)"),
) -> dict[str, Any]:
    """Define cotação manual de Etanol Esalq (sobrepõe CEPEA 403 / fallback)."""
    from src.services.company_settings_service import get_company_settings_service

    settings_svc = get_company_settings_service()
    settings_svc.set_esalq_override(empresaCodigo, esalq_pe=esalqPe, esalq_al=esalqAl)
    market = get_market_intelligence()
    payload = await market.refresh_market_indicators(force=True)
    return {
        "success": True,
        "override": settings_svc.get_esalq_overrides(empresaCodigo),
        "indicators": payload,
    }


@router.get("/market/supplier")
async def get_supplier_info(
    empresa_codigo: int = Query(5555, description="Codigo da empresa/filial"),
    fornecedor_codigo: str | None = Query(None, description="Codigo do fornecedor"),
) -> dict[str, Any]:
    """Retorna informacoes do fornecedor da empresa."""
    
    market = get_market_intelligence()
    return market.get_supplier_info(empresa_codigo, fornecedor_codigo)


@router.get("/settings/companies")
async def list_companies() -> list[dict[str, Any]]:
    """Lista empresas configuradas."""
    
    settings_svc = get_company_settings_service()
    return settings_svc.list_companies()


@router.get("/settings/suppliers")
async def list_suppliers(
    empresa_codigo: int | None = Query(None, description="Codigo da empresa (None para fornecedores globais)"),
) -> list[dict[str, Any]]:
    """Lista fornecedores disponiveis (dinamico por empresa)."""
    
    settings_svc = get_company_settings_service()
    return settings_svc.list_suppliers(empresa_codigo)


@router.get("/settings/products")
async def list_fuel_products(
    empresa_codigo: int | None = Query(None, description="Codigo da empresa (None para produtos globais)"),
) -> list[dict[str, Any]]:
    """Lista produtos de combustivel disponiveis (dinamico por empresa)."""
    
    settings_svc = get_company_settings_service()
    return settings_svc.list_fuel_products(empresa_codigo)
